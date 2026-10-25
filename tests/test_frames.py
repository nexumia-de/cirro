"""FrameStore timeline and disk cache.

Members for other times are made from the recorded RV member by
rewriting only its time attributes, exactly where DWD stores them
(docs/data-sources.md, tar contents)."""
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

h5py = pytest.importorskip("h5py")

from cirro import frames  # noqa: E402

SAMPLE = Path(__file__).parent / "data" / "composite_rv_20261024_2110_000-hd5"
T0 = datetime(2026, 10, 24, 21, 10, tzinfo=timezone.utc)
STEP = timedelta(minutes=5)


def member(analysis, lead_minutes):
    """(name, bytes) of a member for this analysis time and lead."""
    buffer = io.BytesIO(SAMPLE.read_bytes())
    valid = analysis + timedelta(minutes=lead_minutes)
    with h5py.File(buffer, "r+") as f:
        f["what"].attrs["date"] = analysis.strftime("%Y%m%d").encode()
        f["what"].attrs["time"] = analysis.strftime("%H%M%S").encode()
        what = f["dataset1/what"].attrs
        start = valid - STEP
        what["startdate"] = start.strftime("%Y%m%d").encode()
        what["starttime"] = start.strftime("%H%M%S").encode()
        what["enddate"] = valid.strftime("%Y%m%d").encode()
        what["endtime"] = valid.strftime("%H%M%S").encode()
        f["how"].attrs["simulated"] = b"True" if lead_minutes else b"False"
    name = f"composite_rv_{analysis:%Y%m%d_%H%M}_{lead_minutes:03d}-hd5"
    return name, buffer.getvalue()


def add_tar(store, analysis, leads=range(0, 125, 5)):
    for lead in leads:
        store.add(*member(analysis, lead))


@pytest.fixture
def store(tmp_path):
    return frames.FrameStore(tmp_path / "frames")


def test_rewritten_member_reads_back():
    name, data = member(T0, 35)
    assert name == "composite_rv_20261024_2110_035-hd5"
    assert frames.radar.peek(data) == (T0, T0 + timedelta(minutes=35), True)


def test_tar_gives_now_and_forecast(store):
    add_tar(store, T0)
    timeline = store.timeline()
    assert store.analysis_time == T0
    assert len(timeline) == 25
    assert timeline[0].valid_time == T0 and not timeline[0].forecast
    assert timeline[-1].valid_time == T0 + timedelta(minutes=120)
    assert all(e.forecast for e in timeline[1:])
    assert store.missing_past() == [T0 - k * STEP for k in range(1, 13)]


def test_past_analyses_fill_the_last_hour(store):
    add_tar(store, T0)
    for k in range(1, 13):
        store.add(*member(T0 - k * STEP, 0))
    # Older than an hour: not part of the timeline.
    store.add(*member(T0 - 13 * STEP, 0))
    store.prune()
    timeline = store.timeline()
    assert len(timeline) == 37
    assert timeline[0].valid_time == T0 - timedelta(minutes=60)
    assert store.missing_past() == []


def test_new_analysis_replaces_old_forecast(store, tmp_path):
    add_tar(store, T0)
    t1 = T0 + 2 * STEP          # one analysis was missed
    add_tar(store, t1)
    store.prune()
    timeline = store.timeline()
    assert store.analysis_time == t1
    # The old forecasts for 21:15 and the now-past 21:20 are gone; the
    # old analysis stays as a past frame.
    times = [e.valid_time for e in timeline]
    assert times[0] == T0 and times[1] == t1
    assert all(e.analysis_time == t1 for e in timeline[1:])
    assert store.missing_past()[0] == t1 - STEP
    cached = sorted(p.name for p in (tmp_path / "frames").iterdir())
    assert cached == sorted(e.name for e in timeline)


def test_older_data_does_not_replace_newer(store):
    add_tar(store, T0, leads=[0, 5])
    store.add(*member(T0 - STEP, 10))   # forecast of an older analysis
    entry = store.timeline()[1]
    assert entry.valid_time == T0 + STEP and entry.analysis_time == T0


def test_disk_cache_restores_the_timeline(store, tmp_path):
    add_tar(store, T0)
    store.add(*member(T0 - STEP, 0))
    (tmp_path / "frames" / "composite_rv_20261024_2105_005-hd5").write_bytes(b"junk")
    restored = frames.FrameStore(tmp_path / "frames")
    restored.load_cache(T0 + timedelta(minutes=20))
    assert [e.name for e in restored.timeline()] == \
        [e.name for e in store.timeline()]
    # The unreadable file is gone.
    assert not (tmp_path / "frames" / "composite_rv_20261024_2105_005-hd5").exists()


def test_old_disk_cache_is_dropped(store, tmp_path):
    add_tar(store, T0, leads=[0, 5])
    restored = frames.FrameStore(tmp_path / "frames")
    restored.load_cache(T0 + timedelta(hours=4))
    assert restored.analysis_time is None and restored.timeline() == []
    assert list((tmp_path / "frames").iterdir()) == []


def test_entry_decodes(store):
    entry = store.add(*member(T0, 0))
    assert entry.decode().valid_time == T0


def test_rejects_foreign_names(store):
    with pytest.raises(ValueError):
        store.add("../evil", SAMPLE.read_bytes())
