"""Place store: persistence, fallbacks and the own location."""
import json

import pytest

gi = pytest.importorskip("gi")

from cirro.places import OWN, PlaceStore, coordinates  # noqa: E402


def test_missing_file_gives_only_the_own_location(tmp_path):
    store = PlaceStore(tmp_path / "places.json")
    assert store.model.get_n_items() == 1
    assert store.own.own and store.own.position is None
    assert store.own.title == "My Location"
    assert store.default is store.own
    assert not (tmp_path / "places.json").exists()


def test_round_trip(tmp_path):
    path = tmp_path / "cirro" / "places.json"
    store = PlaceStore(path)
    berlin = store.add(52.52, 13.405, default_name="Berlin")
    home = store.add(48.0, 8.0, custom_name="Home")
    store.default = home
    store.update_own(50.0, 9.0)

    again = PlaceStore(path)
    assert [p.title for p in again.places()] == ["Berlin", "Home"]
    assert again.places()[0].id == berlin.id
    assert again.default.id == home.id
    assert again.own.position == (50.0, 9.0)
    assert again.location_enabled
    assert json.loads(path.read_text())["version"] == 1


def test_title_falls_back_to_coordinates(tmp_path):
    store = PlaceStore(tmp_path / "places.json")
    place = store.add(52.5, -13.25)
    assert place.title == coordinates(52.5, -13.25) == "52.50° N, 13.25° W"
    place.default_name = "Somewhere"
    assert place.title == "Somewhere"
    place.custom_name = "Mine"
    assert place.title == "Mine"
    assert store.unnamed() == []


def test_corrupt_file_is_kept_aside(tmp_path):
    path = tmp_path / "places.json"
    path.write_text("{not json")
    store = PlaceStore(path)
    assert store.model.get_n_items() == 1
    assert (tmp_path / "places.json.bad").read_text() == "{not json"


def test_unknown_version_is_not_read(tmp_path):
    path = tmp_path / "places.json"
    path.write_text(json.dumps({"version": 99, "places": [
        {"id": "a", "latitude": 1, "longitude": 2}]}))
    assert PlaceStore(path).places() == []


def test_broken_place_is_skipped(tmp_path):
    path = tmp_path / "places.json"
    path.write_text(json.dumps({"version": 1, "places": [
        {"latitude": 1, "longitude": 2},
        {"id": "b", "latitude": 3, "longitude": 4}]}))
    assert [p.id for p in PlaceStore(path).places()] == ["b"]


def test_deleted_default_falls_back_to_own(tmp_path):
    path = tmp_path / "places.json"
    store = PlaceStore(path)
    place = store.add(1.0, 2.0)
    store.default = place
    store.remove(place)
    assert store.default is store.own
    assert PlaceStore(path).default.id == OWN


def test_remove_and_restore(tmp_path):
    store = PlaceStore(tmp_path / "places.json")
    a, b, c = (store.add(i, i) for i in range(3))
    position = store.remove(b)
    assert store.places() == [a, c]
    store.restore(b, position)
    assert store.places() == [a, b, c]
    with pytest.raises(ValueError):
        store.remove(store.own)


def test_reorder(tmp_path):
    path = tmp_path / "places.json"
    store = PlaceStore(path)
    a, b, c = (store.add(i, i) for i in range(3))
    store.reorder(c, 1)
    assert store.places() == [c, a, b]
    store.reorder(c, 99)
    assert store.places() == [a, b, c]
    store.reorder(store.own, 3)
    assert store.model.get_item(0) is store.own
    assert [p.id for p in PlaceStore(path).places()] == [a.id, b.id, c.id]


def test_move_keeps_custom_name_and_clears_default_name(tmp_path):
    store = PlaceStore(tmp_path / "places.json")
    place = store.add(1.0, 2.0, default_name="Old", custom_name="Mine")
    store.move(place, 3.0, 4.0)
    assert place.position == (3.0, 4.0)
    assert place.default_name == "" and place.custom_name == "Mine"
    assert store.unnamed() == [place]


def test_own_location_moved_by_hand_until_the_next_fix(tmp_path):
    path = tmp_path / "places.json"
    store = PlaceStore(path)
    assert store.update_own(50.0, 9.0)
    store.own.default_name = "Fulda"
    store.move(store.own, 51.0, 10.0)
    assert store.own.manual
    assert PlaceStore(path).own.manual
    # The next real fix overwrites the hand-set position.
    assert store.update_own(50.0, 9.0)
    assert store.own.position == (50.0, 9.0) and not store.own.manual


def test_small_moves_keep_the_own_name(tmp_path):
    store = PlaceStore(tmp_path / "places.json")
    store.update_own(50.0, 9.0)
    store.own.default_name = "Fulda"
    assert not store.update_own(50.003, 9.003)
    assert store.own.default_name == "Fulda"
    assert store.update_own(50.1, 9.0)
    assert store.own.default_name == ""


def test_read_only_store_never_writes(tmp_path):
    path = tmp_path / "places.json"
    path.write_text(json.dumps({"version": 1, "places": [
        {"id": "a", "latitude": 1, "longitude": 2, "default_name": "A"}]}))
    before = path.read_text()
    store = PlaceStore(path, read_only=True)
    store.add(3.0, 4.0)
    store.update_own(5.0, 6.0)
    assert path.read_text() == before
