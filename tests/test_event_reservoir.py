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

    def test_startup_and_manual_button_use_common_read_request(self):
        startup = YAML.split("on_boot:", 1)[1].split("i2c:", 1)[0]
        self.assertIn("script.execute: ${id_prefix}_read_reservoir", startup)
        button = YAML.split('name: "Read Reservoir"', 1)[1].split(
            "- platform: template", 1
        )[0]
        self.assertIn("script.execute: ${id_prefix}_read_reservoir", button)

    def test_common_read_requests_one_native_acquisition(self):
        read = YAML.split("  - id: ${id_prefix}_read_reservoir\n", 1)[1].split(
            "  - id: ${id_prefix}_post_pump_reservoir\n", 1
        )[0]
        self.assertIn("measurement_requested()", read)
        self.assertIn("component.update: reservoir_raw_distance", read)

    def test_post_pump_read_waits_for_named_settling_delay(self):
        self.assertIn("reservoir_settling_delay: 60s", YAML)
        post = YAML.split("  - id: ${id_prefix}_post_pump_reservoir\n", 1)[1].split(
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
            completion.index("script.execute: ${id_prefix}_post_pump_reservoir"),
        )
        self.assertLess(
            completion.index("pump().complete()"),
            completion.index("script.execute: ${id_prefix}_post_pump_reservoir"),
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
