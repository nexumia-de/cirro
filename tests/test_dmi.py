"""DMI's radar composite for Denmark (issue #11), with DMI's recorded
files of 2026-11-22 in tests/data/dmi (docs/data-sources.md, section 8)."""

import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from gi.repository import GObject

from cirro import dmi, dmi_source, projection, provider, radar
from cirro.source_switch import SourceSwitch

DATA = Path(__file__).parent / "data" / "dmi"
FULL = DATA / "dk.com.202611220530.500_max.h5"
DOPPLER = DATA / "dk.com.202611220535.500_max.h5"
PROJDEF = "+proj=stere +ellps=WGS84 +lat_0=56 +lon_0=10.5666 +lat_ts=56"


def test_oblique_stereographic_matches_proj():
    pyproj = pytest.importorskip("pyproj")
    ours = projection.stereographic(radar.parse_projdef(PROJDEF))
    lon = np.array([3.0, 20.735, 4.379, 18.893, 12.57, 10.0])
    lat = np.array([60.0, 59.828, 52.294, 52.159, 55.68, 56.0])
    x, y = ours.forward(lon, lat)
    px, py = pyproj.Proj(PROJDEF)(lon, lat)
    assert np.abs(x - px).max() < 1e-6 and np.abs(y - py).max() < 1e-6
    back_lon, back_lat = ours.inverse(x, y)
    assert np.abs(back_lon - lon).max() < 1e-9 and np.abs(back_lat - lat).max() < 1e-9


def test_decode_full_range_scan():
    frame = radar.decode(FULL.read_bytes())
    assert frame.valid_time == datetime(2026, 11, 22, 5, 30, tzinfo=UTC)
    assert not frame.forecast and frame.analysis_time == frame.valid_time
    assert (frame.grid.xsize, frame.grid.ysize) == (1984, 1728)
    assert frame.grid.xscale == frame.grid.yscale == 500
    rate = frame.mm_per_hour()
    assert 0.46 < np.isnan(rate).mean() < 0.47  # outside the radars' range
    assert 5.0 < np.nanmax(rate) < 5.5


def test_peek_and_sample():
    data = FULL.read_bytes()
    assert radar.peek(data)[2] is False
    copenhagen, far_away = (55.676, 12.568), (40.0, 10.0)
    rates = radar.sample_points(data, [copenhagen, far_away])
    assert rates[0] == 0.0 and math.isnan(rates[1])
    assert radar.sample(data, *copenhagen) == 0.0


def test_z_r_relation():
    # Marshall-Palmer from the file: 23 dBZ ≈ 1 mm/h.
    assert dmi.rate(23.0) == pytest.approx(1.0, abs=0.05)


def test_grid_corners_are_cell_centres():
    # UL (3 E, 60 N) and LR lie 1983 × 1727 cells apart.
    stere = projection.stereographic(radar.parse_projdef(PROJDEF))
    (ulx, uly), (lrx, lry) = stere.forward(3.0, 60.0), stere.forward(18.89328087, 52.15916121)
    assert round((lrx - ulx) / 500) == 1983 and round((uly - lry) / 500) == 1727


def test_reprojection_bounds():
    frame = radar.decode(FULL.read_bytes())
    r = projection.reproject_grid(frame.grid, width=200)
    assert 59.9 < r.north < 60.5 and 52.0 < r.south < 52.3
    assert 2.9 < r.west < 3.1 and 20.6 < r.east < 20.9


def test_scans_from_recorded_item_list():
    found = dmi_source.scans((DATA / "items.json").read_bytes())
    assert found and all(name.startswith("dk.com.") for name, _ in found)
    times = [t for _, t in found]
    assert times == sorted(times)
    assert all(t.minute % 10 == 0 for t in times)  # full-range only


def test_doppler_scan_is_a_different_scan_type():
    found = {name for name, _ in dmi_source.scans((DATA / "items.json").read_bytes())}
    assert DOPPLER.name not in found


@pytest.mark.parametrize(
    "place, expected",
    [
        ((55.676, 12.568), "dmi"),  # Copenhagen
        ((56.16, 10.20), "dmi"),  # Aarhus
        ((55.40, 10.39), "dmi"),  # Odense: RV has no data there
        ((54.91, 9.79), "dwd"),  # Sønderborg: inside RV
        ((52.52, 13.40), "dwd"),  # Berlin
        ((59.33, 18.07), "dwd"),  # Stockholm: outside Denmark
    ],
)
def test_provider(place, expected):
    assert provider.for_point(*place) == expected


class FakeSource(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
    }
    loading = GObject.Property(type=bool, default=False)
    stale = GObject.Property(type=bool, default=False)

    def __init__(self):
        super().__init__()
        self.store, self.calls = object(), []

    def start(self):
        self.calls.append("start")

    def set_active(self, active):
        self.calls.append(("active", active))

    def set_metered(self, metered):
        self.calls.append(("metered", metered))

    def refresh(self):
        self.calls.append("refresh")


def test_source_switch():
    dwd, dmi_ = FakeSource(), FakeSource()
    switch = SourceSwitch({"dwd": dwd, "dmi": lambda: dmi_})
    changed = []
    switch.connect("changed", lambda *_: changed.append(switch.provider))
    switch.start()
    switch.set_active(True)
    switch.set_provider("dmi")
    assert switch.provider == "dmi" and switch.store is dmi_.store
    assert ("active", False) in dwd.calls and "start" in dmi_.calls
    assert ("active", True) in dmi_.calls and changed == ["dmi"]
    dmi_.stale = True
    assert switch.stale
    switch.refresh()
    assert "refresh" in dmi_.calls and "refresh" not in dwd.calls
