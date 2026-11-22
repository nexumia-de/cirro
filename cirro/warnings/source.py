"""Keeps DWD's CAP warning status current: one zip for all places,
polled with `If-None-Match` while the window is visible and kept on
disk, so warnings show at once after a start and without a network
(docs/warnings.md)."""

import logging
import threading
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path

from gi.repository import GLib, GObject

from cirro import USER_AGENT
from cirro.warnings import cap

log = logging.getLogger(__name__)

URL = (
    "https://opendata.dwd.de/weather/alerts/cap/COMMUNEUNION_DWD_STAT/"
    "Z_CAP_C_EDZW_LATEST_PVW_STATUS_PREMIUMDWD_COMMUNEUNION_EN.zip"
)
# The status changes up to 200 times a day; every 10 min keeps warnings
# current at 0.2–0.8 MB per change, a 304 costs almost nothing.
POLL = timedelta(minutes=10)
RETRY = timedelta(minutes=2)
# On a metered connection with "Save Mobile Data" on (issue #34).
METERED_POLL = timedelta(minutes=30)
DIRECTORY = Path(GLib.get_user_cache_dir()) / "cirro" / "warnings"


def fetch(etag=None, url=URL, timeout=30):
    """(zip bytes, ETag), or None while the ETag is unchanged."""
    headers = {"User-Agent": USER_AGENT}
    if etag:
        headers["If-None-Match"] = etag
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("ETag")
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return None
        raise


class DiskCache:
    """The last status zip and its ETag."""

    def __init__(self, directory=DIRECTORY):
        self._zip = Path(directory) / "status-EN.zip"
        self._etag = Path(directory) / "status-EN.etag"

    def load(self):
        try:
            data = self._zip.read_bytes()
        except OSError:
            return None, None
        try:
            etag = self._etag.read_text().strip() or None
        except OSError:
            etag = None
        return data, etag

    def save(self, data, etag):
        try:
            self._zip.parent.mkdir(parents=True, exist_ok=True)
            partial = self._zip.with_suffix(".part")
            partial.write_bytes(data)
            partial.replace(self._zip)
            self._etag.write_text(etag or "")
        except OSError as error:
            log.warning("warnings cache: %s", error)


class WarningSource(GObject.Object):
    """`changed` when the warnings were (re)loaded; `warnings` holds the
    parsed list. With `live=False` (recorded demo data) it never polls."""

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, cache=None, live=True, fetcher=fetch):
        super().__init__()
        self.warnings = []
        self._cache = cache or DiskCache()
        self._live = live
        self._fetch = fetcher
        self._etag = None
        self._active = False
        self._holders = set()  # who wants polling: window, notify
        self._timer = 0
        self._loading = False
        self._metered = False
        if live:
            data, etag = self._cache.load()
            if data:
                self._apply(data, etag)

    def _apply(self, data, etag):
        try:
            self.warnings = cap.parse_zip(data)
        except Exception as error:  # corrupt zip or XML
            log.warning("warnings: %s", error)
            return False
        self._etag = etag
        return True

    def set_metered(self, metered):
        if metered == self._metered:
            return
        self._metered = metered
        if self._active and self._timer and not metered:
            self._schedule(POLL)

    def hold(self, holder, wanted):
        """Poll while anyone wants it: the visible window, notifications."""
        if wanted:
            self._holders.add(holder)
        else:
            self._holders.discard(holder)
        self._set_active(bool(self._holders))

    def _set_active(self, active):
        if active == self._active or not self._live:
            return
        self._active = active
        if active:
            self._poll()
        elif self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0

    def _schedule(self, delay):
        if self._timer:
            GLib.source_remove(self._timer)
        self._timer = GLib.timeout_add_seconds(int(delay.total_seconds()), self._on_timer)

    def _on_timer(self):
        self._timer = 0
        self._poll()
        return GLib.SOURCE_REMOVE

    def _poll(self):
        if self._loading:
            return
        self._loading = True
        etag = self._etag

        def work():
            try:
                result = ("ok", self._fetch(etag))
            except Exception as error:  # network, server
                log.warning("warnings: %s", error)
                result = ("failed", None)
            GLib.idle_add(self._done, *result)

        threading.Thread(target=work, name="warnings", daemon=True).start()

    def _done(self, state, result):
        self._loading = False
        if state == "ok" and result is not None:
            data, etag = result
            if self._apply(data, etag):
                self._cache.save(data, etag)
                self.emit("changed")
        if self._active:
            poll = METERED_POLL if self._metered else POLL
            self._schedule(poll if state == "ok" else RETRY)
        return GLib.SOURCE_REMOVE
