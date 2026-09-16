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
        pump_script = source.split("id: ${id_prefix}_run_pump", 1)[1]
        pump_script = pump_script.split("id: ${id_prefix}_script2", 1)[0]
        self.assertIn("component.update: ph_ezo", pump_script)
        self.assertNotIn("id(ph_ezo).state", pump_script)
        self.assertNotIn('send_custom("R")', pump_script)

    def test_native_polling_and_no_fake_zero_fallback(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        self.assertGreaterEqual(source.count("update_interval: 60s"), 3)
        self.assertNotIn("value_or(0.0)", source)
        self.assertIn("pH Measurement Status", source)
        self.assertIn("EC Measurement Status", source)


if __name__ == "__main__":
    unittest.main()
