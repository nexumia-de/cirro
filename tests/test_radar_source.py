"""RadarSource refresh cycle with the downloads replaced by recorded
members (see test_frames.py), driven by a GLib main loop."""
import urllib.error
from datetime import timedelta

import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
from gi.repository import GLib  # noqa: E402

from cirro import frames, radar_source, source  # noqa: E402
from test_frames import STEP, T0, member  # noqa: E402


def run_until_idle(rs, timeout=10):
    """Run the main loop until the refresh worker has finished."""
    loop = GLib.MainLoop()
    rs.connect("notify::loading", lambda *_: rs.loading or loop.quit())
    GLib.timeout_add_seconds(timeout, loop.quit)
    loop.run()


@pytest.fixture
def fake_dwd(monkeypatch):
    calls = []
    state = {"t0": T0, "missing": {T0 - 3 * STEP}}

    def poll_latest(etag=None, base_url=None):
        calls.append("poll")
        tag = f'"{state["t0"]:%H%M}"'
        return None if etag == tag else source.Latest(state["t0"], tag)

    def fetch_tar(analysis, base_url=None):
        calls.append(f"tar {analysis:%H%M}")
        return [member(analysis, lead) for lead in range(0, 125, 5)]

    def fetch_analysis(analysis, base_url=None):
        calls.append(f"past {analysis:%H%M}")
        if analysis in state["missing"]:
            raise urllib.error.HTTPError("url", 404, "Not Found", None, None)
        return member(analysis, 0)

    monkeypatch.setattr(source, "poll_latest", poll_latest)
    monkeypatch.setattr(source, "fetch_tar", fetch_tar)
    monkeypatch.setattr(source, "fetch_analysis", fetch_analysis)
    return calls, state


def test_refresh_cycle(fake_dwd, tmp_path):
    calls, state = fake_dwd
    now = {"t": T0 + timedelta(minutes=4)}
    rs = radar_source.RadarSource(frames.FrameStore(tmp_path),
                                  now=lambda: now["t"])
    changes = []
    rs.connect("changed", lambda *_: changes.append(len(rs.store.timeline())))

    rs.start()
    run_until_idle(rs)
    assert calls[:2] == ["poll", "tar 2110"]
    assert len([c for c in calls if c.startswith("past")]) == 12
    # 25 frames of the tar plus 11 past analyses; 20:55 is not on the server.
    assert len(rs.store.timeline()) == 36 and changes[-1] == 36
    assert not rs.stale

    # Nothing new: one 304 poll, the missing frame is not asked for again.
    calls.clear()
    rs.refresh()
    run_until_idle(rs)
    assert calls == ["poll"]

    # A new analysis: one tar, and only the frame that became past.
    state["t0"] = T0 + STEP
    now["t"] = T0 + timedelta(minutes=9)
    calls.clear()
    rs.refresh()
    run_until_idle(rs)
    assert calls == ["poll", "tar 2115"]
    assert rs.store.analysis_time == T0 + STEP


def test_stale_and_failure(fake_dwd, tmp_path, monkeypatch):
    rs = radar_source.RadarSource(frames.FrameStore(tmp_path),
                                  now=lambda: T0 + timedelta(minutes=45))
    rs.start()
    run_until_idle(rs)
    assert rs.stale

    def offline(*_, **__):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(source, "poll_latest", offline)
    failures = []
    rs.connect("failed", lambda _, message, show: failures.append(show))
    rs.refresh()
    run_until_idle(rs)
    # A failed manual refresh is shown; the old frames stay.
    assert failures == [True] and len(rs.store.timeline()) == 36
