"""Notifications (issue #25): the rain check on DWD's recorded WMS point
series and the decisions what to notify."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cirro.notify import alerts, rain
from cirro.notify.watcher import load_state, save_state
from cirro.warnings import cap

DATA = Path(__file__).parent / "data"
# GetFeatureInfo of Radar_rv_product_1x1km_ger at 47.3127 N 6.9089 E,
# analysis 2026-11-22 04:50 UTC, +0 … +120 min (raining throughout).
SERIES = DATA / "wms" / "info-rv-series.json"
T0 = datetime(2026, 11, 22, 4, 50, tzinfo=UTC)
CAP = DATA / "cap" / "Z_CAP_C_EDZW_LATEST_PVW_STATUS_PREMIUMDWD_COMMUNEUNION_EN.zip"


def test_parse_recorded_series():
    series = rain.parse_series(SERIES.read_bytes())
    assert len(series) == 25
    assert series[0][0] == T0 and series[-1][0] == T0 + timedelta(minutes=120)
    # mm per 5 min × 12; matches the RV file at that cell (1.308 mm/h).
    assert abs(series[0][1] - 1.308) < 0.001
    assert all(rate >= 0 for _, rate in series)


def test_no_notification_while_it_rains():
    series = rain.parse_series(SERIES.read_bytes())
    assert rain.starts_in(series, T0 + timedelta(minutes=1)) is None


def test_rain_starting_soon():
    def at(minutes, rate):
        return (T0 + timedelta(minutes=minutes), rate)

    dry_then_rain = [
        at(0, 0.0),
        at(5, 0.0),
        at(10, 0.0),
        at(15, 0.0),
        at(20, 0.3),
        at(25, 1.0),
        at(60, 0.0),
    ]
    assert rain.starts_in(dry_then_rain, T0 + timedelta(minutes=2)) == 18
    assert rain.starts_in(dry_then_rain, T0 - timedelta(minutes=30)) is None
    drizzle = [at(0, 0.0), at(10, 0.05)]
    assert rain.starts_in(drizzle, T0) is None


def test_series_url_asks_for_two_hours():
    url = rain.series_url(50.1, 8.7, T0, "2026-11-22T04:50:00.000Z")
    assert "request=GetFeatureInfo" in url
    assert url.endswith("time=2026-11-22T04:50:00.000Z/2026-11-22T06:50:00.000Z")


def test_one_rain_notification_per_shower():
    state = alerts.State()
    assert alerts.rain_due(20, False, state)
    assert not alerts.rain_due(15, False, state)
    assert not alerts.rain_due(None, True, state)  # dry again
    assert alerts.rain_due(10, False, state)


def test_rain_text():
    assert alerts.rain_text(20, "Home") == ("Rain in about 20 min", "At Home")
    assert alerts.rain_text(0, "Home")[0] == "Rain now"


def test_new_warnings_once_and_from_level_two():
    warnings = cap.parse_zip(CAP.read_bytes())
    now = datetime(2026, 11, 22, 4, 45, tzinfo=UTC)
    found = cap.at_point(warnings, 47.99, 7.85, now)  # Freiburg: level 1 only
    state = alerts.State()
    assert alerts.new_warnings(found, state) == []
    assert alerts.new_warnings(found, alerts.State(), min_level=1) == found
    assert {w.identifier for w in found} <= state.warnings
    assert alerts.new_warnings(found, state, min_level=1) == []


def test_updates_of_a_notified_warning_are_not_new():
    warnings = cap.parse_zip(CAP.read_bytes())
    update = next(w for w in warnings if w.msg_type == "Update" and w.references)
    state = alerts.State({update.references[0]})
    assert alerts.new_warnings([update], state, min_level=1) == []


def test_state_on_disk(tmp_path):
    path = tmp_path / "notified.json"
    assert load_state(path) == alerts.State()
    save_state(alerts.State({"a", "b"}, True), path)
    assert load_state(path) == alerts.State({"a", "b"}, True)
