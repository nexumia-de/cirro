"""Map area of a layer request."""
import pytest

from cirro.layers import geometry


def test_mercator_round_trip():
    x, y = geometry.to_mercator(51.5, 12.25)
    assert geometry.from_mercator(x, y) == pytest.approx((51.5, 12.25))


def test_view_size_and_bounds():
    view = geometry.view(51.2, 10.4, 5.8, 360, 400)
    assert view.size == (360, 400)
    north, west, south, east = view.bounds
    assert south < 51.2 < north and west < 10.4 < east
    west_m, south_m, east_m, north_m = view.bbox
    # 360 px at zoom 5.8: 360 × 40075 km / (256 × 2^5.8) ≈ 1.0e6 m.
    assert east_m - west_m == pytest.approx(1.0e6, rel=0.02)


def test_view_is_capped():
    view = geometry.view(51, 10, 8, 1000, 700, scale=2)
    assert max(view.size) == geometry.MAX_PIXELS


def test_rotated_view_covers_the_corners():
    plain = geometry.view(51, 10, 8, 300, 400)
    rotated = geometry.view(51, 10, 8, 300, 400, rotation=0.3)
    assert rotated.bbox[2] - rotated.bbox[0] > plain.bbox[2] - plain.bbox[0]


def test_view_clamps_at_the_poles():
    view = geometry.view(85, 0, 2, 400, 800)
    assert view.bbox[3] == pytest.approx(geometry.HALF)
