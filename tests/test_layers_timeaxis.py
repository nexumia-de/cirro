"""Time dimensions of WMS layers."""
from datetime import datetime, timedelta, timezone

import pytest

from cirro.layers.timeaxis import (MAX_STEPS, TimeAxis, format_time,
                                   latest_at, parse_duration, parse_time)

UTC = timezone.utc


def t(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.mark.parametrize("text, delta", [
    ("PT5M", timedelta(minutes=5)), ("PT1H", timedelta(hours=1)),
    ("PT3H", timedelta(hours=3)), ("P1D", timedelta(days=1)),
    ("P1DT12H", timedelta(days=1, hours=12)),
])
def test_durations(text, delta):
    assert parse_duration(text) == delta


@pytest.mark.parametrize("text", ["P1M", "P1Y", "PT", "P", "PT0M"])
def test_durations_without_fixed_length_are_rejected(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_time_round_trip():
    assert parse_time("2026-11-07T12:00:00.000Z") == t("2026-11-07T12:00")
    assert format_time(t("2026-11-07T12:00")) == "2026-11-07T12:00:00.000Z"


def test_interval_steps_within_window():
    axis = TimeAxis.parse("2025-07-02T16:10:00.000Z/2026-11-07T11:45:00.000Z/PT5M")
    times = axis.times(t("2026-11-07T10:58"), t("2026-11-07T12:00"))
    assert times[0] == t("2026-11-07T11:00")
    assert times[-1] == t("2026-11-07T11:45")
    assert len(times) == 10
    assert axis.step == timedelta(minutes=5)
    assert axis.last == t("2026-11-07T11:45")


def test_list_of_instants():
    axis = TimeAxis.parse("2025-11-05T00:00:00.000Z,2025-11-06T00:00:00.000Z,"
                          "2025-11-07T00:00:00.000Z")
    assert axis.step == timedelta(days=1)
    assert axis.times(t("2025-11-05T12:00"), t("2025-11-08T00:00")) == \
        [t("2025-11-06T00:00"), t("2025-11-07T00:00")]


def test_steps_are_capped():
    axis = TimeAxis.parse("2020-01-01T00:00:00Z/2026-01-01T00:00:00Z/PT5M")
    assert len(axis.times(t("2020-01-01T00:00"), t("2026-01-01T00:00"))) == MAX_STEPS


def test_nearest_within_tolerance():
    axis = TimeAxis.parse("2026-11-07T00:00:00Z/2026-11-08T00:00:00Z/PT1H")
    assert axis.nearest(t("2026-11-07T12:20")) == t("2026-11-07T12:00")
    assert axis.nearest(t("2026-11-07T12:40")) == t("2026-11-07T13:00")
    assert axis.nearest(t("2026-11-09T00:00")) == t("2026-11-08T00:00")
    assert axis.nearest(t("2026-11-09T00:00"), timedelta(hours=1)) is None


def test_latest_at():
    times = [t("2026-11-07T10:00"), t("2026-11-07T11:00"), t("2026-11-07T12:00")]
    assert latest_at(times, t("2026-11-07T11:30")) == 1
    assert latest_at(times, t("2026-11-07T09:00")) == 0
    assert latest_at(times, t("2026-11-08T00:00")) == 2
