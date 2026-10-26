"""Point nowcast: value series from recorded frames and the sentence.

Uses the recorded analysis of 2026-10-24 19:40 UTC in tests/data/demo
(a rain band over western Germany) with its 12 previous analyses."""
import math
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("h5py")

from cirro import colors, nowcast, radar  # noqa: E402
from cirro.frames import FrameStore  # noqa: E402

DEMO = Path(__file__).parent / "data" / "demo"
T0 = datetime(2026, 10, 24, 19, 40, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def timeline():
    store = FrameStore()
    for path in sorted(DEMO.glob("composite_rv_2026*.tar")):
        with tarfile.open(path) as tar:
            try:
                for member in tar:
                    store.add(member.name, tar.extractfile(member).read(),
                              save=False)
            except tarfile.ReadError:
                pass    # past tars are cut after their first member
    assert store.analysis_time == T0
    return store.timeline()


def values_at(timeline, latitude, longitude):
    return nowcast.series(timeline, T0, latitude, longitude)


def test_sample_matches_decode(timeline):
    entry = timeline[12]
    frame = entry.decode()
    row, col = radar.cell(frame.grid, 51.23, 6.78)     # Düsseldorf
    expected = float(frame.mm_per_hour()[row, col])
    assert radar.sample(entry.data, 51.23, 6.78) == pytest.approx(expected)
    assert expected >= nowcast.RAIN
    # Far outside the composite.
    assert radar.cell(frame.grid, 40.0, -20.0) is None
    assert math.isnan(radar.sample(entry.data, 40.0, -20.0))


def test_series_spans_the_timeline(timeline):
    values = values_at(timeline, 52.52, 13.40)          # Berlin, dry
    assert len(values) == 37
    assert [v.minutes for v in values] == list(range(-60, 125, 5))
    assert [v.forecast for v in values] == [False] * 13 + [True] * 24
    assert all(v.rate == 0 for v in values)
    assert nowcast.summary(values) == "No rain expected in the next 2 hours"


@pytest.mark.parametrize("place, latitude, longitude, text", [
    ("Frankfurt", 50.11, 8.68, "Rain starts in 35 min"),
    ("Mainz", 50.00, 8.27, "Rain starts in 1 h 5 min"),
    ("Bremen", 53.08, 8.80, "Rain starts in 1 h 25 min"),
    ("Köln", 50.94, 6.96, "Rain for the next 2 hours"),
])
def test_summary_on_recorded_frames(timeline, place, latitude, longitude, text):
    assert nowcast.summary(values_at(timeline, latitude, longitude)) == text


def test_cache_and_cancel(timeline):
    cache = {}
    first = nowcast.series(timeline, T0, 50.11, 8.68, cache)
    assert len(cache) == 37

    def fail(*_):
        raise AssertionError("sampled again")
    assert nowcast.series(timeline, T0, 50.11, 8.68, cache, sample=fail) == first
    assert nowcast.series(timeline, T0, 50.11, 8.68,
                          cancelled=lambda: True) is None


def made_up(rates):
    """Values from now on, 5 min apart, for the sentence logic only."""
    return [nowcast.Value(T0 + timedelta(minutes=5 * i), 5 * i, i > 0, rate)
            for i, rate in enumerate(rates)]


@pytest.mark.parametrize("rates, text", [
    ([0.0] * 25, "No rain expected in the next 2 hours"),
    ([0.0, 0.05, 0.09, 0.1] + [0.0] * 21, "Rain starts in 15 min"),
    ([1.0] * 25, "Rain for the next 2 hours"),
    ([1.0, 2.0, 0.0, 0.0] + [0.0] * 21, "Rain stops in 10 min"),
    # One dry frame inside a shower is no stop.
    ([1.0, 0.0, 1.0, 0.0, 0.0] + [0.0] * 20, "Rain stops in 15 min"),
    ([1.0] * 24 + [0.0], "Rain stops in 2 h"),
    ([1.0], "Raining now"),
    ([0.0], "No rain now"),
    ([math.nan] * 25, None),
    ([], None),
])
def test_summary(rates, text):
    assert nowcast.summary(made_up(rates)) == text


def test_summary_with_a_shorter_forecast():
    assert nowcast.summary(made_up([0.0] * 13)) == \
        "No rain expected in the next 1 hour"
    assert nowcast.summary(made_up([1.0] * 12)) == "Rain for the next 55 min"


def test_summary_ignores_the_past():
    past = [nowcast.Value(T0 - timedelta(minutes=5), -5, False, 3.0)]
    assert nowcast.summary(past + made_up([0.0] * 25)) == \
        "No rain expected in the next 2 hours"


@pytest.mark.parametrize("minutes, text", [
    (5, "5 min"), (60, "1 h"), (85, "1 h 25 min"), (120, "2 h")])
def test_duration(minutes, text):
    assert nowcast.duration(minutes) == text


def test_bar_height_and_colour():
    assert nowcast.bar_height(0.0) == 0 == nowcast.bar_height(math.nan)
    assert nowcast.bar_height(0.1) == pytest.approx(0.1, abs=0.01)
    heights = [nowcast.bar_height(r) for r in (0.1, 1, 10, 50, 200)]
    assert heights == sorted(heights) and heights[-1] == 1
    assert colors.rgb(0.09) is None and colors.rgb(math.nan) is None
    assert colors.rgb(0.1) == colors.SCALE[0][1]
    assert colors.rgb(12) == colors.SCALE[5][1]
