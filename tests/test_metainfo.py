"""Release notes for the About dialog, and the recorded demo data."""
from pathlib import Path

import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
from gi.repository import GLib  # noqa: E402

from cirro import metainfo, radar_source  # noqa: E402
from test_radar_source import run_until_idle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_release_notes_of_the_newest_release(tmp_path):
    path = tmp_path / "m.xml"
    path.write_text("""<component><releases>
      <release version="0.2.0~dev.1" type="development"><description>
        <ul><li>Radar &amp; more.</li></ul>
      </description></release>
      <release version="0.1.0"><description><p>Old.</p></description></release>
    </releases></component>""")
    assert metainfo.release_notes(path) == (
        "0.2.0~dev.1", "<ul><li>Radar &amp; more.</li></ul>")


def test_release_notes_of_the_source_tree():
    version, markup = metainfo.release_notes(metainfo.find("de.nexumia.Cirro"))
    assert version and markup.startswith("<")


@pytest.mark.parametrize("text", [None, "<component/>", "not xml"])
def test_no_release_notes(tmp_path, text):
    path = None
    if text is not None:
        path = tmp_path / "m.xml"
        path.write_text(text)
    assert metainfo.release_notes(path) is None


def test_demo_data_is_a_complete_current_timeline():
    """tests/data/demo, the recorded data the screenshots show
    (CIRRO_DEMO_DATA), read through the real download code."""
    source = radar_source.demo(ROOT / "tests" / "data" / "demo")
    changed = []
    source.connect("changed", lambda *_: changed.append(True))
    source.set_active(True)
    source.start()
    run_until_idle(source)
    # Drain the idle callbacks the worker queued.
    while GLib.MainContext.default().iteration(False):
        pass
    timeline = source.store.timeline()
    # 12 past analyses, the analysis and 24 forecasts.
    assert len(timeline) == 37
    assert not source.stale and changed
