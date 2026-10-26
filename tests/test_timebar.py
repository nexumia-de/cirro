"""Labels and playback timing of the time bar."""
from datetime import timedelta

import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")

from cirro.frames import Entry  # noqa: E402
from cirro.timebar import (END_PAUSE_FRAMES, MAX_TICK_SECONDS,  # noqa: E402
                           STEP_SECONDS, advance, blend, describe, due,
                           step_frames)
from test_frames import T0  # noqa: E402


def entry(minutes, forecast):
    valid = T0 + timedelta(minutes=minutes)
    return Entry("x", T0 if forecast else valid, valid, forecast, b"")


@pytest.mark.parametrize("minutes, forecast, text", [
    (-35, False, "35 min ago"),
    (0, False, "Now"),
    (40, True, "Forecast +40 min"),
])
def test_describe(minutes, forecast, text):
    assert describe(entry(minutes, forecast), T0) == text


def all_ready(index):
    return True


def test_advance_moves_fractionally():
    assert advance(2.0, 0.25, 10, all_ready) == pytest.approx(2.25)
    assert advance(2.9, 0.25, 10, all_ready) == pytest.approx(3.15)


def test_advance_waits_for_next_frame():
    # Fading 4 → 5 needs frame 5: wait on frame 4 itself.
    ready = lambda i: i != 5  # noqa: E731
    assert advance(3.8, 0.5, 10, ready) == 4.0
    assert advance(4.0, 0.5, 10, ready) == 4.0
    # A large step does not skip a missing frame either.
    assert advance(1.0, 6.0, 10, ready) == 4.0


def test_advance_never_moves_back():
    # Frame 3 got evicted while fading 2 → 3: hold the position.
    assert advance(2.5, 0.1, 10, lambda i: i != 3) == 2.5


def test_advance_holds_the_last_frame_then_loops():
    last = 9
    held = advance(last + 0.0, 1.0, 10, lambda i: i <= last)
    assert last < held < last + END_PAUSE_FRAMES
    assert blend(held, 10) == (last, 0.0)
    assert advance(last + END_PAUSE_FRAMES - 0.1, 0.2, 10, all_ready) == 0.0


@pytest.mark.parametrize("position, index, fraction", [
    (0.0, 0, 0.0), (3.25, 3, 0.25), (8.5, 8, 0.5), (9.0, 9, 0.0), (10.5, 9, 0.0),
])
def test_blend(position, index, fraction):
    got = blend(position, 10)
    assert got[0] == index
    assert got[1] == pytest.approx(fraction)


def test_step_frames():
    # At 60 Hz and normal speed one step takes STEP_SECONDS * 60 ticks.
    assert step_frames(1 / 60, 1.0) * 60 * STEP_SECONDS == pytest.approx(1.0)
    assert step_frames(1 / 60, 2.0) == pytest.approx(2 * step_frames(1 / 60, 1.0))
    # A stall does not jump ahead.
    assert step_frames(5.0, 1.0) == step_frames(MAX_TICK_SECONDS, 1.0)


@pytest.mark.parametrize("hz, every", [(60, 2), (120, 4), (30, 1)])
def test_due_caps_updates_at_30_per_second(hz, every):
    tick_us = 1e6 / hz
    assert not due(tick_us * (every - 1)) or every == 1
    assert due(tick_us * every)
