"""Keeps the FrameStore current: loads the disk cache, polls DWD while the
window is visible and fetches missing past frames
(docs/radar-architecture.md, RadarSource)."""
import logging
import os
import threading
import time
import urllib.error
from datetime import datetime, timezone

from gi.repository import GLib, GObject

from cirro import source

log = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


def _rss_mb():
    try:
        with open("/proc/self/statm") as statm:
            pages = int(statm.read().split()[1])
    except OSError:
        return float("nan")
    return pages * os.sysconf("SC_PAGE_SIZE") / 1e6


class RadarSource(GObject.Object):
    """Signals `changed` when the timeline changed and `failed` when a
    refresh failed; `stale` is True while the newest analysis is older
    than source.STALE_AFTER (or there is none after the first attempt)."""

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
    }

    loading = GObject.Property(type=bool, default=False)
    stale = GObject.Property(type=bool, default=False)

    def __init__(self, store, base_url=source.BASE_URL, now=_now):
        super().__init__()
        self.store = store
        self._base_url = base_url
        self._now = now
        self._etag = None
        self._active = False
        self._timer = 0
        self._due = None           # monotonic time of the next poll
        self._unavailable = set()  # past analyses the server does not have

    def start(self):
        """Load the disk cache, then poll."""
        self._run(self._load_cache_worker, manual=False)

    def set_active(self, active):
        """Poll only while the window is visible; catch up on resume."""
        if active == self._active:
            return
        self._active = active
        if not active:
            self._cancel_timer()
        elif self._due is not None and not self.loading:
            self._schedule_at(self._due)

    def refresh(self):
        """Poll now (the reload button)."""
        self._run(self._poll_worker, manual=True)

    # Scheduling

    def _cancel_timer(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0

    def _schedule_at(self, due):
        self._cancel_timer()
        self._due = due
        if not self._active:
            return
        delay = max(0, due - GLib.get_monotonic_time() / 1e6)
        self._timer = GLib.timeout_add_seconds(max(1, round(delay)),
                                               self._on_timer)

    def _on_timer(self):
        self._timer = 0
        self._run(self._poll_worker, manual=False)
        return GLib.SOURCE_REMOVE

    def _run(self, worker, manual):
        if self.loading:
            return
        self.loading = True
        self._cancel_timer()
        threading.Thread(target=worker, args=(manual,), daemon=True).start()

    # Workers: everything below runs off the main thread except the
    # callbacks passed to GLib.idle_add.

    def _load_cache_worker(self, manual):
        try:
            self.store.load_cache(self._now())
        except Exception:
            log.exception("cannot load the frame cache")
        if self.store.analysis_time:
            GLib.idle_add(self.emit, "changed")
        self._poll_worker(manual)

    def _poll_worker(self, manual):
        error = None
        try:
            latest = source.poll_latest(self._etag, self._base_url)
            if latest and latest.analysis_time != self.store.analysis_time:
                for name, data in source.fetch_tar(latest.analysis_time,
                                                   self._base_url):
                    self.store.add(name, data)
                self.store.prune()
                GLib.idle_add(self.emit, "changed")
            if latest:
                self._etag = latest.etag
            self._fetch_past()
        except Exception as error_:  # network, HTTP or format errors
            log.warning("radar refresh failed: %s", error_)
            error = str(error_)
        GLib.idle_add(self._finished, error, manual)

    def _fetch_past(self):
        missing = self.store.missing_past()
        self._unavailable &= set(missing)
        for time_ in missing:
            if time_ in self._unavailable:
                continue
            try:
                name, data = source.fetch_analysis(time_, self._base_url)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                # A gap in DWD's archive: do not ask again every poll.
                log.info("past frame %s unavailable: %s", time_, error)
                self._unavailable.add(time_)
                continue
            self.store.add(name, data)
            GLib.idle_add(self.emit, "changed")
        self.store.prune()

    def _finished(self, error, manual):
        self.loading = False
        if log.isEnabledFor(logging.DEBUG):
            log.debug("%d frames; %.1f MB received, RSS %.0f MB, CPU %.1f s",
                      len(self.store.timeline()), source.received_bytes() / 1e6,
                      _rss_mb(), time.process_time())
        now = self._now()
        self.stale = source.is_stale(self.store.analysis_time, now)
        delay = source.next_poll(self.store.analysis_time, now)
        self._schedule_at(GLib.get_monotonic_time() / 1e6 + delay.total_seconds())
        if error:
            # Background failures only show up through the stale guard.
            self.emit("failed", error, manual or self.store.analysis_time is None)
        return GLib.SOURCE_REMOVE
