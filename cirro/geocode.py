"""Place names and place search from Nominatim (OpenStreetMap), within
its usage policy: at most one request per second, a descriptive
User-Agent, results cached, no search-as-you-type (docs/data-sources.md,
section 9). No GTK, so it runs in worker threads and in tests."""
import json
import locale
import logging
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from cirro import USER_AGENT

BASE_URL = "https://nominatim.openstreetmap.org/"
# Reverse lookups at zoom 14 (suburb) still list the town or city in the
# address, and reach villages that zoom 10 (city) skips.
REVERSE_ZOOM = 14
# The default name of a place: the first of these address fields.
NAME_FIELDS = ("city", "town", "village", "suburb", "municipality", "county")
SEARCH_LIMIT = 10
# Usage policy: an absolute maximum of 1 request per second.
MIN_INTERVAL = 1.0
ATTRIBUTION = "Place names © OpenStreetMap contributors (ODbL)"

log = logging.getLogger(__name__)

_lock = threading.Lock()
_last = 0.0
_search_cache = {}


def language():
    """Preferred language for names, e.g. "de", from the locale."""
    code = locale.getlocale(locale.LC_MESSAGES)[0] or ""
    code = code.split("_")[0]
    return f"{code},en" if code and code not in ("C", "en") else "en"


def _get(path, params, timeout=20):
    """GET a Nominatim endpoint as JSON, at most once per second across
    all threads."""
    global _last
    url = BASE_URL + path + "?" + urllib.parse.urlencode(
        {"format": "jsonv2", "addressdetails": 1,
         "accept-language": language(), **params})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with _lock:
        wait = _last + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
        finally:
            _last = time.monotonic()
    log.debug("%s: %d bytes", url, len(body))
    return json.loads(body)


def place_name(result):
    """Default name from a reverse or search result: the first of
    NAME_FIELDS in its address, else its own name, else None."""
    if not isinstance(result, dict) or "error" in result:
        return None
    address = result.get("address") or {}
    for field in NAME_FIELDS:
        if address.get(field):
            return address[field]
    return result.get("name") or None


def reverse(latitude, longitude):
    """Default name for a position, or None where Nominatim knows none
    (e.g. at sea). Raises OSError or ValueError when offline or on a bad
    answer, so the caller can try again later."""
    return place_name(_get("reverse", {
        "lat": f"{latitude:.5f}", "lon": f"{longitude:.5f}",
        "zoom": REVERSE_ZOOM}))


@dataclass(frozen=True)
class Result:
    name: str
    detail: str
    latitude: float
    longitude: float


def results(data):
    """Search results from a /search answer."""
    found = []
    for item in data if isinstance(data, list) else []:
        try:
            name = item.get("name") or place_name(item)
            detail = item.get("display_name", "")
            if detail.startswith(f"{name}, "):
                detail = detail[len(name) + 2:]
            found.append(Result(name, detail, float(item["lat"]),
                                float(item["lon"])))
        except (KeyError, TypeError, ValueError):
            continue
    return found


def search(query):
    """Places matching `query`, best first. Cached for the session."""
    query = " ".join(query.split())
    if not query:
        return []
    key = (query.casefold(), language())
    if key not in _search_cache:
        _search_cache[key] = results(_get("search", {
            "q": query, "limit": SEARCH_LIMIT}))
    return _search_cache[key]
