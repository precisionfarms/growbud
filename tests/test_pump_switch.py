import unittest
from pathlib import Path


SOURCE = (Path(__file__).parents[1] / "growbud.yaml").read_text()


class GrowBudManualPumpSwitchTests(unittest.TestCase):
    def test_floating_component_source_is_refreshed_with_remote_package(self):
        external = SOURCE.split("external_components:", 1)[1].split(
            "growbud:", 1
        )[0]
        self.assertIn("refresh: always", external)

    def setUp(self):
        switch_section = SOURCE.split("switch:", 1)[1].split("sensor:", 1)[0]
        self.gpio = switch_section.split("- platform: gpio", 1)[1].split(
            "- platform: template", 1
        )[0]
        self.manual = switch_section.split("- platform: template", 1)[1].split(
            "- platform: gpio", 1
        )[0]

    def test_physical_relay_remains_internal_and_restore_off(self):
        self.assertIn("pin: GPIO26", self.gpio)
        self.assertIn("internal: true", self.gpio)
        self.assertIn("restore_mode: ALWAYS_OFF", self.gpio)

    def test_manual_on_uses_only_the_guarded_run_script(self):
        self.assertIn("name: Pump", self.manual)
        self.assertIn("${id_prefix}_run_pump).execute", self.manual)
        on_action = self.manual.split("turn_on_action:", 1)[1].split(
            "turn_off_action:", 1
        )[0]
        self.assertNotIn("pump_switch).turn_on", on_action)
        self.assertNotIn("switch.turn_on", on_action)

    def test_state_tracks_the_physical_relay(self):
        self.assertIn(
            "return id(${id_prefix}_pump_switch).state;", self.manual
        )
        self.assertNotIn("optimistic: true", self.manual)
        self.assertIn("restore_mode: DISABLED", self.manual)

    def test_manual_off_stops_and_synchronizes_the_guarded_run(self):
        off_action = self.manual.split("turn_off_action:", 1)[1]
        self.assertIn("script.stop: ${id_prefix}_run_pump", off_action)
        self.assertIn("switch.turn_off: ${id_prefix}_pump_switch", off_action)
        self.assertIn("pump().complete()", off_action)
        self.assertIn("component.update: ph_ezo", off_action)

    def test_existing_local_safety_and_entry_points_remain(self):
        watchdog = SOURCE.split("id: ${id_prefix}_pump_watchdog", 1)[1].split(
            "- interval: 30min", 1
        )[0]
        self.assertIn("watchdog_should_stop", watchdog)
        self.assertIn("pump_switch).turn_off()", watchdog)
        self.assertNotIn("api", watchdog.lower())
        self.assertNotIn("wifi", watchdog.lower())
        self.assertIn("mode: single", SOURCE)
        self.assertIn("bounded_duration_seconds", SOURCE)
        run_button = SOURCE.split('name: "Run Pump"', 1)[1].split(
            "- platform: template", 1
        )[0]
        self.assertIn("${id_prefix}_run_pump).execute", run_button)
        self.assertIn("evaluate_irrigation", SOURCE)


if __name__ == "__main__":
    unittest.main()
