"""Labels of the time bar."""
from datetime import timedelta

import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")

from cirro.frames import Entry  # noqa: E402
from cirro.timebar import describe  # noqa: E402
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
