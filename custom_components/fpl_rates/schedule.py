"""FPL RTR-1 time-of-use schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TARIFF_TIME_ZONE = ZoneInfo("America/New_York")


def _tariff_time(moment: datetime) -> datetime:
    """Convert an aware datetime to the tariff's Eastern time zone."""
    if moment.utcoffset() is None:
        raise ValueError("Tariff schedule requires a timezone-aware datetime")
    return moment.astimezone(TARIFF_TIME_ZONE)


@dataclass(frozen=True)
class PeriodInfo:
    """Current schedule state."""

    is_peak: bool
    period: str
    season: str
    holiday: str | None
    weekend: bool
    schedule: str
    next_period: str
    next_change: datetime


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = (
        date(year + 1, 1, 1) - timedelta(days=1)
        if month == 12
        else date(year, month + 1, 1) - timedelta(days=1)
    )
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def tariff_holiday(day: date) -> str | None:
    """Return a named RTR-1 holiday.

    The tariff names the holiday itself, rather than an observed weekday.
    """
    holidays = {
        date(day.year, 1, 1): "New Year's Day",
        _last_weekday(day.year, 5, 0): "Memorial Day",
        date(day.year, 7, 4): "Independence Day",
        _nth_weekday(day.year, 9, 0, 1): "Labor Day",
        _nth_weekday(day.year, 11, 3, 4): "Thanksgiving Day",
        date(day.year, 12, 25): "Christmas Day",
    }
    return holidays.get(day)


def is_peak(moment: datetime) -> bool:
    """Return whether the supplied instant is RTR-1 on-peak in Eastern Time."""
    moment = _tariff_time(moment)
    if moment.weekday() >= 5 or tariff_holiday(moment.date()):
        return False

    clock = moment.time().replace(tzinfo=None)
    if 4 <= moment.month <= 10:
        return time(12) <= clock < time(21)
    return (
        time(6) <= clock < time(10)
        or time(18) <= clock < time(22)
    )


def next_change(moment: datetime) -> datetime:
    """Find the next peak-state transition, returned in Eastern Time."""
    moment = _tariff_time(moment)
    current = is_peak(moment)
    candidate = moment.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(9 * 24 * 60):
        if is_peak(candidate) != current:
            return candidate
        candidate += timedelta(minutes=1)
    return candidate


def period_info(moment: datetime) -> PeriodInfo:
    """Return period details for the supplied instant in Eastern Time."""
    moment = _tariff_time(moment)
    peak = is_peak(moment)
    summer = 4 <= moment.month <= 10
    return PeriodInfo(
        is_peak=peak,
        period="Peak" if peak else "Off-peak",
        season="Summer" if summer else "Winter",
        holiday=tariff_holiday(moment.date()),
        weekend=moment.weekday() >= 5,
        schedule=(
            "Weekdays 12:00 PM–9:00 PM ET"
            if summer
            else "Weekdays 6:00 AM–10:00 AM and 6:00 PM–10:00 PM ET"
        ),
        next_period="Off-peak" if peak else "Peak",
        next_change=next_change(moment),
    )
