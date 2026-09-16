import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import esphome


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

    def test_lighting_local_civil_conversion_and_dst(self):
        summer = datetime(2026, 9, 15, 5, tzinfo=ZONE)
        winter = datetime(2026, 1, 15, 5, tzinfo=ZONE)

        self.assertEqual(int(summer.timestamp()), 1789470000)
        self.assertEqual(summer.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M"), "2026-09-15 11:00")
        self.assertEqual(int(winter.timestamp()), 1768478400)
        self.assertEqual(winter.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M"), "2026-01-15 12:00")

        bloom_off = datetime.fromtimestamp(int(summer.timestamp()) + 13 * 3600, ZONE)
        self.assertEqual(bloom_off.strftime("%Y-%m-%d %H:%M"), "2026-09-15 18:00")

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

        fall_start = date(2026, 10, 15)
        fall_harvest = fall_start + timedelta(days=30)
        fall_local = datetime(fall_harvest.year, fall_harvest.month, fall_harvest.day, tzinfo=ZONE)
        self.assertEqual(fall_harvest, date(2026, 11, 14))
        self.assertEqual((fall_local.hour, fall_local.utcoffset()), (0, timedelta(hours=-7)))

    def test_overnight_lighting_window_on_both_sides_of_midnight(self):
        def local(day: int, hour: int, minute: int) -> datetime:
            return datetime(2026, 9, day, hour, minute, tzinfo=ZONE)

        self.assertTrue(lighting_is_on(local(15, 23, 59), 20, 18))
        self.assertTrue(lighting_is_on(local(16, 0, 1), 20, 18))
        self.assertTrue(lighting_is_on(local(16, 13, 59), 20, 18))
        self.assertFalse(lighting_is_on(local(16, 14, 0), 20, 18))

    def test_sntp_owns_the_single_configured_timezone(self):
        source = (Path(__file__).parents[1] / "growbud.yaml").read_text()
        self.assertNotIn("mktime(", source)
        self.assertIn("recalc_timestamp_local()", source)
        self.assertNotIn("set_timezone(", source)
        self.assertEqual(sum(line.lstrip().startswith("timezone:") for line in source.splitlines()), 2)
        self.assertIn("timezone: ${timezone}", source)

    def test_esphome_local_conversion_uses_parsed_timezone(self):
        esphome_package = Path(esphome.__file__).parent
        time_cpp = (esphome_package / "core/time.cpp").read_text()
        rtc_cpp = (esphome_package / "components/time/real_time_clock.cpp").read_text()

        local_conversion = time_cpp.split("void ESPTime::recalc_timestamp_local()", 1)[1]
        local_conversion = local_conversion.split("int32_t ESPTime::timezone_offset()", 1)[0]
        self.assertIn("time::get_global_tz()", local_conversion)
        self.assertIn("time::is_in_dst", local_conversion)
        self.assertNotIn("::mktime(", local_conversion)
        self.assertIn("set_global_tz(parsed)", rtc_cpp)


if __name__ == "__main__":
    unittest.main()
