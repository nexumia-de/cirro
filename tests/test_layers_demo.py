"""Demo mode of the map layers: recorded GeoServer answers in
tests/data/demo/layers (issue #74)."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cirro.layers import demo, wms

DEMO = Path(__file__).parent / "data" / "demo"
LAYER = "Icon-eu_reg00625_fd_gl_T"


@pytest.fixture
def demo_mode(monkeypatch):
    monkeypatch.setenv("CIRRO_DEMO_DATA", str(DEMO))
    demo.directory.cache_clear()
    demo._recorded.cache_clear()
    yield
    demo.directory.cache_clear()
    demo._recorded.cache_clear()


def test_off_without_demo_data(monkeypatch):
    monkeypatch.delenv("CIRRO_DEMO_DATA", raising=False)
    demo.directory.cache_clear()
    assert not demo.active()
    demo.directory.cache_clear()


def test_file_names():
    assert demo.file_for(wms.capabilities_url(LAYER)) == f"caps-{LAYER}.xml"
    assert demo.file_for(wms.legend_url(LAYER)) == f"legend-{LAYER}.json"
    url = wms.map_url([LAYER], (0, 0, 1, 1), (2, 2),
                      datetime(2026, 11, 22, 5, tzinfo=timezone.utc))
    assert demo.file_for(url) == f"map-{LAYER}-20261122T0500.png"


def test_recorded_answers(demo_mode):
    assert demo.now() == datetime(2026, 11, 22, 4, 53, tzinfo=timezone.utc)
    caps = wms.fetch_capabilities(LAYER)
    assert caps.reference_time == "2026-11-22T00:00:00.000Z"
    assert wms.fetch_legend(LAYER)
    view = demo.view()
    for hour in (4, 5, 6):
        url = wms.map_url([LAYER], view.bbox, view.size,
                          datetime(2026, 11, 22, hour, tzinfo=timezone.utc),
                          reference_time=caps.reference_time)
        assert wms.fetch_map(url).startswith(b"\x89PNG")
    north, west, south, east = view.bounds
    assert 55.9 < north < 56.1 and 46.4 < south < 46.6
