import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
YAML = (ROOT / "growbud.yaml").read_text()
COMPONENT = (ROOT / "components/growbud/growbud.cpp").read_text()


class GrowBudEventReservoirTests(unittest.TestCase):
    def test_automatic_polling_is_disabled(self):
        ultrasonic = YAML.split("- platform: ultrasonic", 1)[1].split(
            "- platform: ezo", 1
        )[0]
        self.assertIn("update_interval: never", ultrasonic)
        self.assertNotIn("update_interval: 30s", ultrasonic)

    def test_derived_entities_are_not_polled(self):
        sensor_section = YAML.split("sensor:", 1)[1].split("text_sensor:", 1)[0]
        for name in ("Reservoir Distance", "Reservoir Level", "Reservoir Volume"):
            entity = sensor_section.split(f'name: "{name}"', 1)[1].split(
                "  - platform:", 1
            )[0]
            self.assertIn("update_interval: never", entity)
            self.assertNotIn("lambda:", entity)

        status = YAML.split('name: "Reservoir Measurement Status"', 1)[1].split(
            "  - platform:", 1
        )[0]
        self.assertIn("update_interval: never", status)
        self.assertNotIn("lambda:", status)

    def test_acquisition_result_publishes_all_derived_entities(self):
        ultrasonic = YAML.split("- platform: ultrasonic", 1)[1].split(
            "- platform: ezo", 1
        )[0]
        self.assertIn("script.execute: ${id_prefix}_publish_reservoir", ultrasonic)

        publication = YAML.split(
            "  - id: ${id_prefix}_publish_reservoir\n", 1
        )[1].split("  - id: ${id_prefix}_read_reservoir\n", 1)[0]
        for entity_id in (
            "reservoir_distance",
            "reservoir_level",
            "reservoir_volume",
            "reservoir_measurement_status",
        ):
            self.assertIn(f"id({entity_id}).publish_state", publication)

    def test_calibration_changes_publish_derived_state(self):
        number_section = YAML.split("number:", 1)[1].split("datetime:", 1)[0]
        calibration_ids = (
            "reservoir_full_distance",
            "reservoir_empty_distance",
            "reservoir_capacity",
        )
        for index, calibration_id in enumerate(calibration_ids):
            block = number_section.split(f"id: {calibration_id}", 1)[1]
            if index + 1 < len(calibration_ids):
                block = block.split(f"id: {calibration_ids[index + 1]}", 1)[0]
            else:
                block = block.split("id: veg_transition", 1)[0]
            self.assertIn("script.execute: ${id_prefix}_publish_reservoir", block)

    def test_no_idle_reservoir_refresh_loop_remains(self):
        derived = YAML.split('name: "Reservoir Distance"', 1)[1].split(
            'name: "pH Measurement Status"', 1
        )[0]
        self.assertNotIn("update_interval: 15s", derived)

    def test_startup_and_manual_button_use_common_read_request(self):
        startup = YAML.split("on_boot:", 1)[1].split("i2c:", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_read_reservoir", startup)
        button = YAML.split('name: "Read Reservoir"', 1)[1].split(
            "- platform: template", 1
        )[0]
        self.assertIn("script.execute: ${id_prefix}_read_reservoir", button)

    def test_common_read_requests_one_native_acquisition(self):
        read = YAML.split("  - id: ${id_prefix}_read_reservoir\n", 1)[1].split(
            "  - id: ${id_prefix}_chemistry_result_timeout\n", 1
        )[0]
        self.assertIn("measurement_requested()", read)
        self.assertIn("component.update: reservoir_raw_distance", read)

    def test_post_pump_read_waits_for_named_settling_delay(self):
        self.assertIn("reservoir_settling_delay: 60s", YAML)
        post = YAML.split("  - id: ${id_prefix}_post_irrigation_measurements\n", 1)[1].split(
            "  - id: ${id_prefix}_complete_pump_run\n", 1
        )[0]
        self.assertLess(
            post.index("delay: ${reservoir_settling_delay}"),
            post.index("script.execute: ${id_prefix}_read_reservoir"),
        )
        self.assertNotIn("pump_switch", post)

    def test_pump_is_completed_before_settling_is_scheduled(self):
        completion = YAML.split("  - id: ${id_prefix}_complete_pump_run\n", 1)[1].split(
            "  - id: ${id_prefix}_run_pump\n", 1
        )[0]
        self.assertLess(
            completion.index("switch.turn_off: ${id_prefix}_pump_switch"),
            completion.index("script.execute: ${id_prefix}_post_irrigation_measurements"),
        )
        self.assertLess(
            completion.index("pump().complete()"),
            completion.index("script.execute: ${id_prefix}_post_irrigation_measurements"),
        )

    def test_failure_preserves_value_and_drives_event_stale_semantics(self):
        self.assertIn("this->measurement_failed_ = true", COMPONENT)
        failure = COMPONENT.split("bool ReservoirState::record_distance", 1)[1].split(
            "void ReservoirState::update_median_", 1
        )[0]
        self.assertNotIn("filtered_distance_cm_ = 0", failure)
        status = COMPONENT.split("MeasurementStatus ReservoirState::status", 1)[1].split(
            "float ReservoirState::level_fraction", 1
        )[0]
        self.assertIn("this->measurement_failed_", status)
        self.assertNotIn("millis", status)
        self.assertNotIn("FRESHNESS", status)


if __name__ == "__main__":
    unittest.main()
