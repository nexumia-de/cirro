"""Decoder, projection and colour scale, tested with the recorded RV member."""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("h5py")

from wetterblick import colors, projection, radar  # noqa: E402

SAMPLE = Path(__file__).parent / "data" / "composite_rv_20261024_2110_000-hd5"


@pytest.fixture(scope="module")
def frame():
    return radar.decode(SAMPLE.read_bytes())


@pytest.fixture(scope="module")
def reprojection(frame):
    return projection.reproject_grid(frame.grid, width=700)


def test_decode_times_and_flags(frame):
    utc = timezone.utc
    assert frame.analysis_time == datetime(2026, 10, 24, 21, 10, tzinfo=utc)
    assert frame.valid_time == frame.analysis_time
    assert not frame.forecast


def test_decode_values(frame):
    assert frame.raw.dtype == np.uint16 and frame.raw.shape == (1200, 1100)
    # Row 0 (north edge) lies outside the coverage.
    assert (frame.raw[0] == radar.NODATA).all()
    rate = frame.mm_per_hour()
    assert np.isnan(rate[0]).all()
    assert np.nanmin(rate) == 0
    # Largest raw value in this file is 1559 → 1.558 mm per 5 min.
    assert int(frame.raw[frame.raw != radar.NODATA].max()) == 1559
    assert np.nanmax(rate) == pytest.approx(1.558 * 12, rel=1e-5)


def test_grid_edges_from_corners(frame):
    # docs/data-sources.md: the grid spans x ∈ [−500, 1099500] m,
    # y ∈ [−1199500, 500] m.
    assert (frame.grid.x_min, frame.grid.y_max) == (-500.0, 500.0)


def test_stereographic_matches_recorded_corners(frame):
    stere = projection.Stereographic(radar.parse_projdef(frame.grid.projdef))
    # Corner coordinates as stored in /where (degrees, outer edges).
    corners = {(55.8621, 1.4633): (-500, 500),
               (45.6846, 16.5809): (1099500, -1199500)}
    for (lat, lon), expected in corners.items():
        assert stere.forward(lon, lat) == pytest.approx(expected, abs=20)


def test_stereographic_matches_pyproj(frame):
    pyproj = pytest.importorskip("pyproj")
    proj = pyproj.Proj(frame.grid.projdef)
    stere = projection.Stereographic(radar.parse_projdef(frame.grid.projdef))
    lon = np.array([1.5, 6.1, 10.0, 13.4, 18.7])
    lat = np.array([55.8, 47.3, 50.0, 52.5, 45.7])
    np.testing.assert_allclose(stere.forward(lon, lat), proj(lon, lat), atol=1e-3)


def test_stereographic_inverse_roundtrip(frame):
    stere = projection.Stereographic(radar.parse_projdef(frame.grid.projdef))
    lon = np.array([2.0, 9.9, 17.5])
    lat = np.array([46.0, 51.0, 55.5])
    back = projection.stere_inverse(stere, *stere.forward(lon, lat))
    np.testing.assert_allclose(back, (lon, lat), atol=1e-9)


def test_mercator_roundtrip():
    lon, lat = np.array([-170.0, 0.0, 10.4]), np.array([-60.0, 0.0, 51.2])
    back = projection.mercator_lonlat(*projection.mercator_xy(lon, lat))
    np.testing.assert_allclose(back, (lon, lat), atol=1e-9)


def test_reprojection_bounds_cover_the_grid(reprojection):
    r = reprojection
    assert r.index.size == r.width * r.height
    assert r.west == pytest.approx(1.4633, abs=1e-3)
    assert r.east == pytest.approx(18.7316, abs=1e-3)
    assert r.south == pytest.approx(45.6846, abs=1e-3)
    # The north edge bulges above the corners between them.
    assert r.north > 55.8621


def test_reprojection_samples_the_right_cell(frame, reprojection):
    """A target pixel's centre must fall into the source cell it shows."""
    r = reprojection
    stere = projection.Stereographic(radar.parse_projdef(frame.grid.projdef))
    x0, y0 = projection.mercator_xy(r.west, r.north)
    x1, y1 = projection.mercator_xy(r.east, r.south)
    for px, py in [(100, 100), (350, 300), (600, 500)]:
        lon, lat = projection.mercator_lonlat(x0 + (px + .5) * (x1 - x0) / r.width,
                                              y0 + (py + .5) * (y1 - y0) / r.height)
        sx, sy = stere.forward(lon, lat)
        col = int((sx - frame.grid.x_min) // 1000)
        row = int((frame.grid.y_max - sy) // 1000)
        assert r.index[py * r.width + px] == row * frame.grid.xsize + col


def test_colour_scale(frame):
    lut = colors.rgba_lut(frame.gain, frame.offset, frame.undetect)
    assert lut[radar.NODATA, 3] == 0 and lut[frame.undetect, 3] == 0
    # raw → mm/h: (raw × 0.001 − 0.001) × 12.
    def raw_for(rate):
        return int(np.ceil((rate / 12 - frame.offset) / frame.gain))
    assert lut[raw_for(0.1) - 1, 3] == 0
    for bound, rgb in colors.SCALE:
        assert tuple(lut[raw_for(bound)]) == (*rgb, colors.ALPHA)


def test_colorize(frame, reprojection):
    image = colors.colorize(frame, reprojection)
    assert image.shape == (reprojection.height, reprojection.width, 4)
    assert image.dtype == np.uint8
    # Corners of the bounding box are outside the stereographic grid.
    assert image[0, 0, 3] == 0 and image[-1, -1, 3] == 0
    assert (image[..., 3] > 0).any()
