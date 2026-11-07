"""WMS requests and answers, with GeoServer answers recorded on
2026-11-07 (tests/data/wms/)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from cirro.layers import wms

DATA = Path(__file__).parent / "data" / "wms"
UTC = timezone.utc


def caps(layer):
    return wms.parse_capabilities((DATA / f"caps-{layer}.xml").read_bytes(), layer)


def query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_nowcast_layer_has_a_five_minute_axis():
    result = caps("Blitzdichte")
    assert result.axis.step == timedelta(minutes=5)
    assert result.reference_time == ""


def test_forecast_layer_names_its_model_run():
    result = caps("Icon_reg025_fd_sl_T2M")
    assert result.axis.step == timedelta(hours=1)
    assert result.reference_time.endswith("Z")


def test_warnings_have_no_time():
    assert caps("Warnungen_Gemeinden_vereinigt").axis is None


def test_daily_layer():
    assert caps("Pollenflug").axis.step == timedelta(days=1)


def test_unknown_layer():
    with pytest.raises(ValueError):
        wms.parse_capabilities((DATA / "caps-Pollenflug.xml").read_bytes(), "Nope")


def test_map_url():
    url = wms.map_url(("A", "B"), (1.4, 2, 3, 4), (300, 200),
                      datetime(2026, 11, 7, 12, tzinfo=UTC), "s",
                      "EC_II=4", "2026-11-07T06:00:00.000Z")
    q = query(url)
    assert q["layers"] == "dwd:A,dwd:B"
    assert q["styles"] == "s,s"
    assert q["crs"] == "EPSG:3857"
    assert q["bbox"] == "1,2,3,4"
    assert (q["width"], q["height"]) == ("300", "200")
    assert q["time"] == "2026-11-07T12:00:00.000Z"
    assert q["dim_reference_time"] == "2026-11-07T06:00:00.000Z"
    assert q["cql_filter"] == "EC_II=4;EC_II=4"
    assert q["transparent"] == "true"


def test_extra_dimensions():
    q = query(wms.map_url(("A",), (0, 0, 1, 1), (1, 1),
                          dims=(("ENSEMBLE_PRODUCT", "Probabilities:>14m/s"),)))
    assert q["dim_ensemble_product"] == "Probabilities:>14m/s"


def test_newest_model_run_is_used():
    body = b"""<WMS_Capabilities xmlns="http://www.opengis.net/wms"><Capability>
      <Layer><Name>E</Name>
      <Dimension name="time">2026-11-07T00:00:00Z/2026-11-08T00:00:00Z/PT6H</Dimension>
      <Dimension name="REFERENCE_TIME" default="2026-11-05T12:00:00.000Z">2026-11-05T12:00:00.000Z,2026-11-06T00:00:00.000Z,2026-11-07T00:00:00.000Z</Dimension>
      </Layer></Capability></WMS_Capabilities>"""
    assert wms.parse_capabilities(body, "E").reference_time == "2026-11-07T00:00:00.000Z"


def test_timeless_map_url_has_no_time():
    assert "time" not in query(wms.map_url(("A",), (0, 0, 1, 1), (1, 1)))


def test_feature_info_url_is_latitude_first():
    q = query(wms.feature_info_url(("A",), 51.5, 12.5, fields=("EVENT", "SEVERITY")))
    south, west, north, east = map(float, q["bbox"].split(","))
    assert south < 51.5 < north and west < 12.5 < east
    assert q["crs"] == "EPSG:4326"
    assert q["propertyName"] == "EVENT,SEVERITY"


def test_capabilities_url_is_per_layer():
    assert wms.capabilities_url("Blitzdichte").startswith(
        "https://maps.dwd.de/geoserver/dwd/Blitzdichte/wms?")


def test_service_exception_is_raised():
    body = (b'<?xml version="1.0"?><ServiceExceptionReport><ServiceException '
            b'code="InvalidDimensionValue">No data available</ServiceException>'
            b'</ServiceExceptionReport>')
    with pytest.raises(wms.ServiceError, match="No data"):
        wms._check(body, "text/xml")
