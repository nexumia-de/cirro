"""Nominatim answers recorded on 2026-10-26 (tests/data/nominatim)."""
import json
from pathlib import Path

from cirro import geocode

DATA = Path(__file__).parent / "data" / "nominatim"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def test_city_before_suburb():
    assert geocode.place_name(load("reverse-berlin-mitte")) == "Berlin"
    assert geocode.place_name(load("reverse-munich")) == "Munich"


def test_village_before_hamlet_and_municipality():
    assert geocode.place_name(load("reverse-village")) == "St. Peter"


def test_no_name_at_sea():
    assert geocode.place_name(load("reverse-sea")) is None


def test_fallback_to_own_name():
    assert geocode.place_name({"name": "Feldberg", "address": {}}) == "Feldberg"


def test_search_results():
    found = geocode.results(load("search-freiburg"))
    assert found[0].name == "Freiburg im Breisgau"
    assert found[0].detail == "Baden-Württemberg, Germany"
    assert abs(found[0].latitude - 47.996) < 0.01
    assert abs(found[0].longitude - 7.849) < 0.01
    assert len(found) == len(load("search-freiburg"))


def test_no_search_results():
    assert geocode.results(load("search-none")) == []
    assert geocode.results({"error": "x"}) == []


def test_empty_query_sends_nothing(monkeypatch):
    def fail(*_):
        raise AssertionError("no request expected")
    monkeypatch.setattr(geocode, "_get", fail)
    assert geocode.search("   ") == []


def test_search_is_cached(monkeypatch):
    calls = []

    def fake(path, params):
        calls.append(params["q"])
        return load("search-freiburg")
    monkeypatch.setattr(geocode, "_get", fake)
    geocode._search_cache.clear()
    first = geocode.search("Freiburg")
    assert geocode.search("  freiburg ") == first
    assert calls == ["Freiburg"]


def test_requests_are_spaced_one_second(monkeypatch):
    slept = []
    monkeypatch.setattr(geocode.time, "sleep", slept.append)
    monkeypatch.setattr(geocode.time, "monotonic", lambda: 100.0)

    class Response:
        def __init__(self, request, timeout):
            assert request.get_header("User-agent").startswith("Cirro/")
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self):
            return b"[]"
    monkeypatch.setattr(geocode.urllib.request, "urlopen", Response)
    geocode._last = 0.0
    geocode._get("search", {"q": "a"})
    geocode._get("search", {"q": "b"})
    assert slept == [1.0]
