"""The chosen map layers are kept across starts."""
from cirro.layers import catalogue, settings


def test_round_trip(tmp_path):
    path = tmp_path / "settings.ini"
    settings.save("pollen", 3, {"warnings": 1, "lightning": 0}, path)
    assert settings.load(path) == ("pollen", 3, {"warnings": 1, "lightning": 0})


def test_unknown_or_wrong_role_falls_back(tmp_path):
    path = tmp_path / "settings.ini"
    settings.save("warnings", 0, {"pollen": 0, "nope": 2, "lightning": 1}, path)
    assert settings.load(path) == (catalogue.RADAR, 0, {"lightning": 1})


def test_missing_file(tmp_path):
    assert settings.load(tmp_path / "none.ini") == (catalogue.RADAR, 0, {})
