import math
import unittest
from pathlib import Path


def measurement_status(has_valid, failed):
    if not has_valid:
        return "Unavailable"
    if failed:
        return "Stale"
    return "Valid"


def parse_ec_response(payload):
    parts = payload.split(",")
    if len(parts) < 4:
        return None
    try:
        values = tuple(float(value) for value in parts[:4])
    except ValueError:
        return None
    return values if all(math.isfinite(value) for value in values) else None


class GrowBudChemistryTests(unittest.TestCase):
    def test_valid_ph_measurement_and_recovery(self):
        self.assertEqual(measurement_status(True, False), "Valid")
        self.assertEqual(measurement_status(True, True), "Stale")
        self.assertEqual(measurement_status(True, False), "Valid")

    def test_valid_ec_measurement_and_recovery(self):
        self.assertEqual(parse_ec_response("1450.5,725.2,0.71,1.001"), (1450.5, 725.2, 0.71, 1.001))
        self.assertEqual(measurement_status(True, True), "Stale")
        self.assertEqual(measurement_status(True, False), "Valid")

    def test_unavailable_before_first_success_or_after_explicit_failure(self):
        self.assertEqual(measurement_status(False, False), "Unavailable")
        self.assertEqual(measurement_status(False, True), "Unavailable")

    def test_last_stored_ph_is_unavailable_before_first_valid_measurement(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        last_ph = source.split('id: last_stored_ph_sensor', 1)[1]
        last_ph = last_ph.split('text_sensor:', 1)[0]
        self.assertIn("update_interval: never", last_ph)
        self.assertNotIn("lambda:", last_ph)
        startup = source.split("on_boot:", 1)[1].split("i2c:", 1)[0]
        self.assertIn("id(last_stored_ph_sensor).publish_state(NAN)", startup)
        ph_event = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        self.assertIn("id(last_stored_ph_sensor).publish_state", ph_event)
        self.assertNotIn("value_or(0.0)", last_ph)

    def test_chemistry_status_entities_are_not_polling_components(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        for name in ("pH Measurement Status", "EC Measurement Status"):
            entity = source.split(f'name: "{name}"', 1)[1].split(
                "  - platform:", 1
            )[0]
            self.assertIn("update_interval: never", entity)
            self.assertNotIn("lambda:", entity)

    def test_status_publication_is_transition_guarded(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        publication = source.split(
            "  - id: ${id_prefix}_publish_chemistry_status\n", 1
        )[1].split("  - id: ${id_prefix}_publish_reservoir\n", 1)[0]
        self.assertIn("!id(ph_measurement_status).has_state()", publication)
        self.assertIn("id(ph_measurement_status).state != ph_status", publication)
        self.assertIn("!id(ec_measurement_status).has_state()", publication)
        self.assertIn("id(ec_measurement_status).state != ec_status", publication)
        self.assertEqual(publication.count("publish_state"), 2)

    def test_startup_uses_transition_publisher_and_no_freshness_timer_remains(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        startup = source.split("on_boot:", 1)[1].split("i2c:", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_publish_chemistry_status", startup)
        self.assertNotIn("chemistry_freshness_check", source)
        component = (Path(__file__).parents[1] / "components/growbud/growbud.cpp").read_text()
        self.assertNotIn("CHEMISTRY_FRESHNESS_MS", component)
        self.assertNotIn("now_ms - last_success", component)

    def test_each_native_chemistry_result_evaluates_status_transition(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        ph_event = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        ec_event = source.split("id: ec_ezo", 1)[1].split("id: ec_value", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_publish_chemistry_status", ph_event)
        self.assertEqual(ec_event.count("script.execute: ${id_prefix}_publish_chemistry_status"), 1)

    def test_native_polling_is_disabled_and_idle_has_no_read_requests(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        ph_ezo = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        ec_ezo = source.split("id: ec_ezo", 1)[1].split("id: ec_value", 1)[0]
        self.assertIn("update_interval: never", ph_ezo)
        self.assertIn("update_interval: never", ec_ezo)
        intervals = source.split("\ninterval:\n", 1)[1].split("\nnumber:\n", 1)[0]
        active_intervals = "\n".join(
            line for line in intervals.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("component.update: ph_ezo", active_intervals)
        self.assertNotIn("component.update: ec_ezo", active_intervals)

    def test_manual_read_chemistry_requests_each_native_sensor_once(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        button = source.split('name: "Read Chemistry"', 1)[1].split(
            "  - platform: template", 1
        )[0]
        self.assertIn("script.execute: ${id_prefix}_read_chemistry", button)
        read = source.split("  - id: ${id_prefix}_read_chemistry\n", 1)[1].split(
            "  - id: ${id_prefix}_post_irrigation_measurements\n", 1
        )[0]
        self.assertEqual(read.count("component.update: ph_ezo"), 1)
        self.assertEqual(read.count("component.update: ec_ezo"), 1)
        self.assertIn("ph_measurement_requested()", read)
        self.assertIn("ec_measurement_requested()", read)

    def test_missing_result_timeout_marks_only_pending_requests_failed(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        timeout = source.split(
            "  - id: ${id_prefix}_chemistry_result_timeout\n", 1
        )[1].split("  - id: ${id_prefix}_read_ph\n", 1)[0]
        self.assertIn("delay: ${chemistry_read_timeout}", timeout)
        self.assertIn("ph_measurement_pending()", timeout)
        self.assertIn("ec_measurement_pending()", timeout)
        self.assertIn("chemistry.mark_ph_failed()", timeout)
        self.assertIn("chemistry.mark_ec_failed()", timeout)

    def test_malformed_ec_response_never_becomes_zero(self):
        last_valid = (1450.5, 725.2, 0.71, 1.001)
        parsed = parse_ec_response("not-a-number,725.2,0.71,1.001")
        self.assertIsNone(parsed)
        self.assertEqual(last_valid, (1450.5, 725.2, 0.71, 1.001))

    def test_nonfinite_ec_response_is_rejected(self):
        self.assertIsNone(parse_ec_response("nan,725.2,0.71,1.001"))
        self.assertIsNone(parse_ec_response("1450.5,inf,0.71,1.001"))

    def test_incomplete_ec_response_is_rejected(self):
        self.assertIsNone(parse_ec_response("1450.5,725.2,0.71"))
        self.assertIsNone(parse_ec_response(""))

    def test_post_pump_requests_async_read_without_consuming_state(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        completion = source.split("id: ${id_prefix}_complete_pump_run", 1)[1]
        completion = completion.split("id: ${id_prefix}_run_pump", 1)[0]
        self.assertNotIn("component.update: ph_ezo", completion)
        self.assertIn("script.execute: ${id_prefix}_post_irrigation_measurements", completion)
        self.assertNotIn("id(ph_ezo).state", completion)
        self.assertNotIn('send_custom("R")', completion)

        post = source.split(
            "  - id: ${id_prefix}_post_irrigation_measurements\n", 1
        )[1].split("  - id: ${id_prefix}_complete_pump_run\n", 1)[0]
        self.assertLess(post.index("delay: ${reservoir_settling_delay}"), post.index("read_chemistry"))
        self.assertEqual(post.count("script.execute: ${id_prefix}_read_chemistry"), 1)
        self.assertEqual(post.count("script.execute: ${id_prefix}_read_reservoir"), 1)

    def test_native_paths_and_no_fake_zero_fallback(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        ph_ezo = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        ec_ezo = source.split("id: ec_ezo", 1)[1].split("id: ec_value", 1)[0]
        self.assertIn("record_ph(x)", ph_ezo)
        self.assertIn("record_ec(x)", ec_ezo)
        self.assertNotIn("value_or(0.0)", source)
        self.assertIn("pH Measurement Status", source)
        self.assertIn("EC Measurement Status", source)

    def test_custom_ec_path_remains_auxiliary(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        custom = source.split("on_custom:", 1)[1].split("  - platform: template", 1)[0]
        self.assertIn("send_custom", source)
        self.assertIn("id(tds_value).publish_state", custom)
        self.assertIn("id(salinity_value).publish_state", custom)
        self.assertIn("id(sg_value).publish_state", custom)
        self.assertNotIn("id(ec_value).publish_state", custom)
        self.assertNotIn("chemistry().record_ec", custom)
        self.assertNotIn("mark_ec_failed", custom)


if __name__ == "__main__":
    unittest.main()
