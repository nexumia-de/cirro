"""Station measurements (WFS answer recorded 2026-11-07 12:00 UTC)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from cirro.layers import wfs

DATA = json.loads((Path(__file__).parent / "data" / "wms" / "wfs-RBSN_FF.json").read_text())


def test_parse_wind():
    stations = wfs.parse(DATA, "SPEED")
    assert len(stations) == 72
    s = stations[0]
    assert 47 < s.latitude < 56 and 5 < s.longitude < 16
    assert s.direction is not None and s.name


def test_missing_field_is_skipped():
    assert wfs.parse(DATA, "TEMPERATURE") == []
    assert wfs.parse({"features": [{"properties": {"SPEED": "x"},
                                    "geometry": {"coordinates": [1, 2]}}]}, "SPEED") == []


def test_url_filters_one_hour():
    url = wfs.features_url("RBSN_FF", datetime(2026, 11, 7, 12, tzinfo=timezone.utc))
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["CQL_FILTER"] == "M_DATE='2026-11-07T12:00:00Z'"
    assert q["typeNames"] == "dwd:RBSN_FF"


def test_distance():
    # Berlin to Hamburg ≈ 255 km.
    assert wfs.distance_km(52.52, 13.405, 53.55, 9.993) == pytest.approx(255, abs=5)


def test_nearest_within():
    stations = wfs.parse(DATA, "SPEED")
    station, km = wfs.nearest(stations, 50.11, 8.68)
    assert km < 50
    assert wfs.nearest(stations, 40.0, 3.0, within_km=50) == (None, None)
    assert wfs.nearest([], 50, 8) == (None, None)


def test_place_wind_line():
    pytest.importorskip("gi")
    from cirro.place_details import sun_text, wind_text
    stations = wfs.parse(DATA, "SPEED")
    measured = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    text = wind_text(stations, 50.11, 8.68, measured)
    assert text.startswith("Wind ") and " km · " in text
    assert wind_text(stations, 40.0, 3.0, measured) is None
    assert sun_text(78.2, 15.6, datetime(2026, 6, 21).date()) == "No sunset today"
