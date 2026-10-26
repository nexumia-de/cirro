"""Playback speed preference."""
import pytest

pytest.importorskip("h5py")
gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from cirro.main import load_speed, save_speed  # noqa: E402


def test_speed_round_trip(tmp_path):
    path = tmp_path / "cirro" / "settings.ini"
    assert load_speed(path) == 1.0
    save_speed(2.0, path)
    assert load_speed(path) == 2.0


def test_unknown_speed_falls_back(tmp_path):
    path = tmp_path / "settings.ini"
    path.write_text("[playback]\nspeed=7\n")
    assert load_speed(path) == 1.0
