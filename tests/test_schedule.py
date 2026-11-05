"""Tariff time-zone regression tests, runnable without Home Assistant."""

from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from custom_components.fpl_rates import schedule


class ScheduleTimeZoneTests(unittest.TestCase):
    def test_same_instant_has_same_period_in_every_zone(self):
        for instant in (
            "2026-07-06T16:00:00+00:00",  # Summer peak starts at noon EDT.
            "2026-07-07T01:00:00+00:00",  # Summer peak ends at 9 PM EDT.
            "2026-11-05T11:00:00+00:00",  # Winter peak starts at 6 AM EST.
            "2026-11-05T15:00:00+00:00",  # Winter morning peak ends.
        ):
            moment = datetime.fromisoformat(instant)
            expected = schedule.period_info(moment)
            for zone in ("America/New_York", "America/Los_Angeles", "Asia/Tokyo"):
                with self.subTest(instant=instant, zone=zone):
                    self.assertEqual(
                        schedule.period_info(moment.astimezone(ZoneInfo(zone))),
                        expected,
                    )

    def test_peak_boundaries_use_eastern_time(self):
        for start, end in (
            ("2026-07-06T16:00:00+00:00", "2026-07-07T01:00:00+00:00"),
            ("2026-11-05T11:00:00+00:00", "2026-11-05T15:00:00+00:00"),
            ("2026-11-05T23:00:00+00:00", "2026-11-06T03:00:00+00:00"),
        ):
            with self.subTest(start=start):
                start = datetime.fromisoformat(start)
                end = datetime.fromisoformat(end)
                self.assertFalse(schedule.is_peak(start - timedelta(seconds=1)))
                self.assertTrue(schedule.is_peak(start))
                self.assertTrue(schedule.is_peak(end - timedelta(seconds=1)))
                self.assertFalse(schedule.is_peak(end))
                self.assertEqual(schedule.next_change(start), end)
                self.assertEqual(str(schedule.next_change(start).tzinfo), "America/New_York")

    def test_calendar_details_use_eastern_date(self):
        for instant, holiday, weekend, season in (
            ("2026-07-04T02:00:00+00:00", None, False, "Summer"),
            ("2026-07-05T02:00:00+00:00", "Independence Day", True, "Summer"),
            ("2026-04-01T02:00:00+00:00", None, False, "Winter"),
        ):
            with self.subTest(instant=instant):
                info = schedule.period_info(datetime.fromisoformat(instant))
                self.assertEqual((info.holiday, info.weekend, info.season),
                                 (holiday, weekend, season))
        self.assertFalse(schedule.is_peak(datetime.fromisoformat("2026-12-25T12:00:00+00:00")))

    def test_next_transition_across_daylight_saving_changes(self):
        for instant, expected in (
            ("2026-03-06T22:00:00-05:00", "2026-03-09T06:00:00-04:00"),
            ("2026-10-30T21:00:00-04:00", "2026-11-02T06:00:00-05:00"),
        ):
            with self.subTest(instant=instant):
                transition = schedule.next_change(datetime.fromisoformat(instant))
                self.assertEqual(transition.isoformat(), expected)

    def test_naive_datetimes_are_rejected(self):
        for function in (schedule.is_peak, schedule.next_change, schedule.period_info):
            with self.subTest(function=function.__name__):
                with self.assertRaisesRegex(ValueError, "timezone-aware"):
                    function(datetime(2026, 7, 6, 12))


if __name__ == "__main__":
    unittest.main()
