import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import subprocess
import tempfile
from zoneinfo import ZoneInfo


ZONE = ZoneInfo("America/Denver")


def local_epoch(day: date, hour: int = 0) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=ZONE).timestamp())


def lighting_is_on(now: datetime, start_hour: int, duration_hours: int) -> bool:
    today_start = datetime(now.year, now.month, now.day, start_hour, tzinfo=ZONE)
    candidates = (today_start, today_start - timedelta(days=1))
    return any(start <= now < start + timedelta(hours=duration_hours) for start in candidates)


class GrowBudTimezoneTests(unittest.TestCase):
    def test_local_midnight_epochs_and_dst(self):
        cases = (
            (date(2026, 1, 15), -7, 1768460400),
            (date(2026, 7, 15), -6, 1784095200),
            (date(2026, 9, 15), -6, 1789452000),
        )
        for day, expected_offset_hours, expected_epoch in cases:
            local = datetime(day.year, day.month, day.day, tzinfo=ZONE)
            self.assertEqual(local.utcoffset(), timedelta(hours=expected_offset_hours))
            self.assertEqual(local_epoch(day), expected_epoch)

    def test_start_bloom_and_harvest_calendar_dates(self):
        start = date(2026, 9, 15)
        bloom = start + timedelta(days=30)
        harvest = bloom + timedelta(days=60)

        self.assertEqual(local_epoch(start), 1789452000)
        self.assertEqual(bloom, date(2026, 10, 15))
        self.assertEqual(local_epoch(bloom), 1792044000)
        self.assertEqual(harvest, date(2026, 12, 14))
        self.assertEqual(local_epoch(harvest), 1797231600)

    def test_calendar_day_addition_preserves_midnight_across_dst(self):
        start = date(2026, 2, 15)
        bloom = start + timedelta(days=30)
        bloom_local = datetime(bloom.year, bloom.month, bloom.day, tzinfo=ZONE)
        self.assertEqual(bloom, date(2026, 3, 17))
        self.assertEqual((bloom_local.hour, bloom_local.utcoffset()), (0, timedelta(hours=-6)))

    def test_overnight_lighting_window_on_both_sides_of_midnight(self):
        def local(day: int, hour: int, minute: int) -> datetime:
            return datetime(2026, 9, day, hour, minute, tzinfo=ZONE)

        self.assertTrue(lighting_is_on(local(15, 23, 59), 20, 18))
        self.assertTrue(lighting_is_on(local(16, 0, 1), 20, 18))
        self.assertTrue(lighting_is_on(local(16, 13, 59), 20, 18))
        self.assertFalse(lighting_is_on(local(16, 14, 0), 20, 18))

    def test_sntp_owns_the_single_configured_timezone(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        self.assertEqual(source.count("mktime("), 7)
        self.assertNotIn("set_timezone(", source)
        self.assertEqual(source.count("timezone:"), 2)
        self.assertIn("timezone: ${timezone}", source)

    def test_growbud_cpp_local_time_semantics(self):
        root = Path(__file__).parents[1]
        esphome_core = root / ".venv/lib/python3.9/site-packages/esphome/core"
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "timezone_semantics"
            subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    str(root / "tests/timezone_semantics.cpp"),
                    str(esphome_core / "time.cpp"),
                    "-I",
                    str(esphome_core.parent.parent),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
