import math
import unittest
from pathlib import Path


FRESHNESS_MS = 180_000


def measurement_status(has_valid, failed, last_success_ms, now_ms):
    if not has_valid or failed:
        return "Unavailable"
    if (now_ms - last_success_ms) & 0xFFFFFFFF > FRESHNESS_MS:
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
        self.assertEqual(measurement_status(True, False, 1_000, 2_000), "Valid")
        self.assertEqual(measurement_status(True, False, 1_000, 182_000), "Stale")
        self.assertEqual(measurement_status(True, False, 200_000, 200_001), "Valid")

    def test_valid_ec_measurement_and_recovery(self):
        self.assertEqual(parse_ec_response("1450.5,725.2,0.71,1.001"), (1450.5, 725.2, 0.71, 1.001))
        self.assertEqual(measurement_status(True, False, 5_000, 185_001), "Stale")
        self.assertEqual(measurement_status(True, False, 190_000, 190_001), "Valid")

    def test_unavailable_before_first_success_or_after_explicit_failure(self):
        self.assertEqual(measurement_status(False, False, 0, 10_000), "Unavailable")
        self.assertEqual(measurement_status(True, True, 9_000, 10_000), "Unavailable")

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

    def test_startup_events_and_freshness_check_use_transition_publisher(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        startup = source.split("on_boot:", 1)[1].split("i2c:", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_publish_chemistry_status", startup)
        freshness = source.split(
            "# Retain time-based chemistry freshness", 1
        )[1].split("id: ${id_prefix}_pump_watchdog", 1)[0]
        self.assertIn("interval: 15s", freshness)
        self.assertIn("script.execute: ${id_prefix}_publish_chemistry_status", freshness)

    def test_each_chemistry_result_evaluates_status_transition(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        ph_event = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        ec_event = source.split("id: ec_ezo", 1)[1].split("id: ec_value", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_publish_chemistry_status", ph_event)
        self.assertEqual(
            ec_event.count("script.execute: ${id_prefix}_publish_chemistry_status"),
            2,
        )

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
        self.assertIn("component.update: ph_ezo", completion)
        self.assertNotIn("id(ph_ezo).state", completion)
        self.assertNotIn('send_custom("R")', completion)

    def test_native_polling_and_no_fake_zero_fallback(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        ph_ezo = source.split("id: ph_ezo", 1)[1].split("id: ec_ezo", 1)[0]
        ec_ezo = source.split("id: ec_ezo", 1)[1].split("id: ec_value", 1)[0]
        self.assertIn("update_interval: 60s", ph_ezo)
        self.assertIn("update_interval: 60s", ec_ezo)
        self.assertNotIn("value_or(0.0)", source)
        self.assertIn("pH Measurement Status", source)
        self.assertIn("EC Measurement Status", source)
        component = (Path(__file__).parents[1] / "components/growbud/growbud.cpp").read_text()
        self.assertIn("CHEMISTRY_FRESHNESS_MS", component)


if __name__ == "__main__":
    unittest.main()
