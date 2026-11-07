"""Sunrise and sunset, and wind in words."""
from datetime import date, datetime, timezone

import pytest

from cirro import sun, wind


def minutes(time_):
    return time_.hour * 60 + time_.minute


@pytest.mark.parametrize("day, rise, set_", [
    # Berlin, UTC; published times ±2 min (timeanddate.com).
    (date(2026, 11, 7), "06:13", "15:27"),
    (date(2026, 6, 21), "02:43", "19:33"),
    (date(2026, 12, 21), "07:16", "14:54"),
])
def test_berlin(day, rise, set_):
    r, s = sun.sun_times(52.52, 13.405, day)
    for got, want in ((r, rise), (s, set_)):
        hours, mins = map(int, want.split(":"))
        assert abs(minutes(got) - (hours * 60 + mins)) <= 2


def test_polar_day_and_night():
    assert sun.sun_times(78.2, 15.6, date(2026, 6, 21)) == ("day", None)
    assert sun.sun_times(78.2, 15.6, date(2026, 12, 21)) == ("night", None)


def test_times_are_utc():
    rise, _ = sun.sun_times(50, 8, date(2026, 3, 20))
    assert rise.tzinfo == timezone.utc and rise.date() == date(2026, 3, 20)


@pytest.mark.parametrize("speed, force", [(0, 0), (0.29, 0), (0.3, 1), (3.3, 2),
                                          (5.5, 4), (17.2, 8), (33, 12)])
def test_beaufort(speed, force):
    assert wind.beaufort(speed) == force


def test_describe():
    assert wind.describe(0.1, 90) == "Calm"
    assert wind.describe(7.0, 22) == "4 Bft (25 km/h) from NNE"
    assert wind.describe(7.0) == "4 Bft (25 km/h)"


def test_now_is_today():
    today = datetime.now(timezone.utc).date()
    assert sun.sun_times(50, 8)[0].date() == today
