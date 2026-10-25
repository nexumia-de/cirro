"""Timeline of radar frames: past analyses, the current analysis and its
forecast (docs/radar-architecture.md, FrameStore).

Each frame is kept as the compressed HDF5 member it was downloaded as
(0.1–0.5 MB) and decoded only when it is drawn, so the 37 frames of the
timeline cost about 15 MB instead of about 100 MB decoded. The members
are also written to a disk cache so the app opens with the last frames
instantly. No GTK; the methods are thread-safe.
"""
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from cirro import radar

STEP = timedelta(minutes=5)
# Past analyses shown before the current one.
PAST = timedelta(minutes=60)
# A cache older than this is not worth showing at start.
MAX_CACHE_AGE = timedelta(hours=3)
_NAME = re.compile(r"composite_rv_\d{8}_\d{4}_\d{3}-hd5")

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Entry:
    name: str                  # member name, unique per analysis and lead
    analysis_time: datetime    # UTC
    valid_time: datetime       # UTC
    forecast: bool
    data: bytes

    def decode(self):
        return radar.decode(self.data)


class FrameStore:
    def __init__(self, cache_dir=None):
        self._lock = threading.Lock()
        self._entries = {}     # valid time → Entry
        self._analysis_time = None
        self._cache_dir = Path(cache_dir) if cache_dir else None

    @property
    def analysis_time(self):
        """Time of the newest analysis, None while there is none."""
        return self._analysis_time

    def add(self, name, data, save=True):
        """Add one downloaded member. A newer analysis replaces what an
        older one forecast for the same time."""
        if not _NAME.fullmatch(name):
            raise ValueError(f"unexpected member name {name!r}")
        analysis, valid, forecast = radar.peek(data)
        entry = Entry(name, analysis, valid, forecast, data)
        with self._lock:
            current = self._entries.get(valid)
            if current is None or analysis >= current.analysis_time:
                self._entries[valid] = entry
            if not forecast and (self._analysis_time is None
                                 or analysis > self._analysis_time):
                self._analysis_time = analysis
        if save and self._cache_dir:
            self._save(entry)
        return entry

    def _wanted(self, entry):
        t0 = self._analysis_time
        if entry.valid_time < t0 - PAST:
            return False
        # Forecasts of older analyses are outdated; the past is shown by
        # the analyses themselves.
        return not entry.forecast or entry.analysis_time == t0

    def timeline(self):
        """Frames from −60 min to the end of the newest forecast, in time
        order. Past analyses may be missing while they download."""
        with self._lock:
            if self._analysis_time is None:
                return []
            return sorted((e for e in self._entries.values() if self._wanted(e)),
                          key=lambda e: e.valid_time)

    def missing_past(self):
        """Times of past analyses (newest first) not yet in the store."""
        with self._lock:
            t0 = self._analysis_time
            if t0 is None:
                return []
            missing = []
            for k in range(1, PAST // STEP + 1):
                time_ = t0 - k * STEP
                entry = self._entries.get(time_)
                if entry is None or entry.forecast:
                    missing.append(time_)
            return missing

    def prune(self):
        """Drop frames that left the timeline, from memory and disk."""
        with self._lock:
            if self._analysis_time is None:
                dropped = list(self._entries.values())
            else:
                dropped = [e for e in self._entries.values()
                           if not self._wanted(e)]
            for entry in dropped:
                del self._entries[entry.valid_time]
            keep = {e.name for e in self._entries.values()}
        if self._cache_dir and self._cache_dir.is_dir():
            for path in self._cache_dir.iterdir():
                if path.name not in keep:
                    path.unlink(missing_ok=True)

    # Disk cache

    def _save(self, entry):
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_dir / entry.name
            temp = path.with_name(path.name + ".tmp")
            temp.write_bytes(entry.data)
            os.replace(temp, path)
        except OSError as error:
            log.warning("cannot write the frame cache: %s", error)

    def load_cache(self, now):
        """Fill the store from the disk cache unless it is older than
        MAX_CACHE_AGE at `now`. Unreadable files are deleted."""
        if not self._cache_dir or not self._cache_dir.is_dir():
            return
        for path in sorted(self._cache_dir.iterdir()):
            if not _NAME.fullmatch(path.name):
                path.unlink(missing_ok=True)
                continue
            try:
                self.add(path.name, path.read_bytes(), save=False)
            except Exception as error:  # truncated or foreign files
                log.warning("dropping cached %s: %s", path.name, error)
                path.unlink(missing_ok=True)
        if self._analysis_time and now - self._analysis_time > MAX_CACHE_AGE:
            with self._lock:
                self._entries.clear()
                self._analysis_time = None
        self.prune()
