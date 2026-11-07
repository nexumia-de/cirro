"""Legends from GetLegendGraphic JSON (recorded 2026-11-07)."""
import json
from pathlib import Path

from cirro.layers import catalogue, legend_data

DATA = Path(__file__).parent / "data" / "wms"


def legend(layer, translations=None):
    data = json.loads((DATA / f"legend-{layer}.json").read_text())
    return legend_data.parse(data, translations)


def test_raster_scale_uses_lower_bounds_and_unit():
    rw = legend("RADOLAN-RW")
    assert rw.kind == "scale"
    assert rw.unit == "mm / 1h"
    assert [e.label for e in rw.entries][:4] == ["0.1", "0.2", "0.5", "1"]
    assert rw.entries[-1].label == "≥100"


def test_temperature_scale():
    t2m = legend("Icon_reg025_fd_sl_T2M")
    assert t2m.entries[0].label == "<-60"
    assert t2m.unit == "°C"


def test_uv_unit_in_english():
    assert legend("UVIndex").unit == "UV index"
    assert [e.label for e in legend("UVIndex").entries] == ["0", "3", "6", "8", "≥11"]


def test_unit_header_entry_is_not_a_class():
    density = legend("Blitzdichte")
    assert density.unit == "per min and 100 km²"
    assert density.entries[0].label == "0.1"


def test_classes_are_translated():
    pollen = legend("Pollenflug", catalogue.POLLEN_LEGEND)
    assert pollen.kind == "classes"
    assert [e.label for e in pollen.entries] == [
        "None", "None to low", "Low", "Low to moderate", "Moderate",
        "Moderate to high", "High"]
    warnings = legend("Warnungen_Gemeinden_vereinigt", catalogue.WARNING_LEGEND)
    assert "Level 3" in [e.label for e in warnings.entries]


def test_thin_keeps_every_nth_label():
    entries = [legend_data.Entry((0, 0, 0), str(i)) for i in range(10)]
    assert legend_data.thin(entries, 4) == ["0", "", "", "3", "", "", "6", "", "", "9"]
    assert legend_data.thin(entries[:3], 4) == ["0", "1", "2"]


def test_empty_legend():
    assert legend_data.parse({"Legend": []}) is None
