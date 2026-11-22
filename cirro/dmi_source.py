"""DMI's radar composite for places in Denmark (issue #11,
docs/decisions/dmi-radar.md): the full-range scans of the last hour from
DMI's STAC API, kept in a FrameStore with a disk cache.

DMI's terms ask mobile apps not to update continuously and never while
not active, so this source fetches only at start, when the window shows
again with data older than REFRESH_AFTER, and on Reload; there is no
timer. Same signals and properties as RadarSource, so the window can use
either (docs/data-sources.md, section 8)."""

import json
import logging
import re
import threading
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from gi.repository import GLib, GObject

from cirro import USER_AGENT
from cirro.frames import PAST, FrameStore

log = logging.getLogger(__name__)

ITEMS_URL = "https://opendataapi.dmi.dk/v1/radardata/collections/composite/items"
DOWNLOAD_URL = "https://opendataapi.dmi.dk/v1/radardata/download/"
NAMES = re.compile(r"dk\.com\.\d{12}\.500_max\.h5")
# Full-range scans (240 km) every 10 min; the Doppler scans in between
# cover only 120 km around each radar.
SCAN_TYPE = "fullRange"
REFRESH_AFTER = timedelta(minutes=10)
# Scans appear 8–13 min after their time; older than this is out of date.
STALE_AFTER = timedelta(minutes=40)
CACHE = Path(GLib.get_user_cache_dir()) / "cirro" / "dmi"


def _now():
    return datetime.now(UTC)


def _get(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def items_url(now):
    start = (now - PAST - timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = {"datetime": f"{start}/..", "limit": 40, "sortorder": "datetime,DESC"}
    return f"{ITEMS_URL}?{urllib.parse.urlencode(query, safe=':/,')}"


def scans(body):
    """STAC item list → [(file name, time)] of the full-range scans."""
    found = []
    for feature in json.loads(body).get("features", []):
        properties = feature.get("properties", {})
        name = feature.get("id", "")
        if properties.get("scanType") != SCAN_TYPE or not NAMES.fullmatch(name):
            continue
        when = datetime.fromisoformat(properties["datetime"].replace("Z", "+00:00"))
        found.append((name, when))
    return sorted(found, key=lambda item: item[1])


class DmiSource(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
    }

    loading = GObject.Property(type=bool, default=False)
    stale = GObject.Property(type=bool, default=False)

    def __init__(self, store=None, now=_now, get=_get):
        super().__init__()
        self.store = store or FrameStore(CACHE, names=NAMES)
        self._now = now
        self._get = get
        self._active = False
        self._fetched = None  # when the last fetch finished

    def start(self):
        self._run(manual=False, load_cache=True)

    def set_active(self, active):
        if active == self._active:
            return
        self._active = active
        if (
            active
            and not self.loading
            and (self._fetched is None or self._now() - self._fetched > REFRESH_AFTER)
        ):
            self._run(manual=False)

    def set_metered(self, metered):
        """Nothing to slow down: DMI is fetched on demand only."""

    def refresh(self):
        self._run(manual=True)

    def _run(self, manual, load_cache=False):
        if self.loading:
            return
        self.loading = True
        threading.Thread(
            target=self._worker, args=(manual, load_cache), name="dmi", daemon=True
        ).start()

    def _worker(self, manual, load_cache):
        if load_cache:
            try:
                self.store.load_cache(self._now())
            except Exception:
                log.exception("cannot load the DMI cache")
            if self.store.analysis_time:
                GLib.idle_add(self.emit, "changed")
        error = None
        try:
            have = {e.name for e in self.store.timeline()}
            added = False
            for name, _time in scans(self._get(items_url(self._now()))):
                if name not in have:
                    self.store.add(name, self._get(DOWNLOAD_URL + name))
                    added = True
            self.store.prune()
            if added:
                GLib.idle_add(self.emit, "changed")
        except Exception as error_:  # network, HTTP or format errors
            log.warning("DMI refresh failed: %s", error_)
            error = str(error_)
        GLib.idle_add(self._finished, error, manual)

    def _finished(self, error, manual):
        self.loading = False
        self._fetched = self._now()
        t0 = self.store.analysis_time
        self.stale = t0 is None or self._now() - t0 > STALE_AFTER
        if error:
            self.emit("failed", error, manual or t0 is None)
        return GLib.SOURCE_REMOVE
