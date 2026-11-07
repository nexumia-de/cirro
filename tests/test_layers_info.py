"""Values under a tap (GetFeatureInfo answers recorded 2026-11-07)."""
import json
from pathlib import Path

import pytest

from cirro.layers import catalogue, info

DATA = Path(__file__).parent / "data" / "wms"


def features(layer):
    return json.loads((DATA / f"info-{layer}.json").read_text())["features"]


def test_number():
    text = info.describe(catalogue.TEMPERATURE, features("Icon_reg025_fd_sl_T2M"))
    assert text.endswith(" °C") and float(text.split()[0]) == pytest.approx(4, abs=10)


def test_wind_from_u_and_v():
    assert info.describe(catalogue.Value("wind"), [{"properties": {"u": 0, "v": -5}}]) \
        == "5.0 m/s from N"
    assert "m/s from" in info.describe(catalogue.Value("wind"),
                                       features("Icon_reg025_fd_sl_UV10M"))


def test_warning():
    assert info.describe(catalogue.Value("warning"),
                         features("Warnungen_Gemeinden_vereinigt")) == "Frost, level 1"
    assert info.describe(catalogue.Value("warning"), []) == "No warning"


def test_pollen():
    assert info.describe(catalogue.Value("pollen"), features("Pollenflug")) == \
        "None · Tiefland Sachsen"


def test_health():
    text = info.describe(catalogue.Value("health"), features("Biowettervorhersage"))
    assert text in ("No effect", "Low risk", "High risk", "Positive effect")


def test_no_value():
    assert info.describe(catalogue.MM, [{"properties": {"TIME": "x"}}]) is None
    assert info.describe(None, []) is None


@pytest.mark.parametrize("degrees, point", [(0, "N"), (22, "NNE"), (90, "E"),
                                            (200, "SSW"), (359, "N")])
def test_compass(degrees, point):
    assert info.compass(degrees) == point


def test_station_text():
    from cirro.layers.wfs import Station
    stations = [Station("Leipzig", 51.3, 12.4, 7.0, 22)]
    wind = catalogue.get("stations-wind").value
    assert info.station_text(wind, stations, 51.31, 12.41) == \
        "4 Bft (25 km/h) from NNE, Leipzig"
    assert info.station_text(wind, stations, 48, 8) is None
    assert info.station_text(catalogue.TEMPERATURE, stations, 51.3, 12.4) == \
        "7 °C, Leipzig"
