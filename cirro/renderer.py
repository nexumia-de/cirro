"""Turns timeline entries into radar textures in a worker thread.

Decoding, reprojecting and colouring a frame takes about 0.1 s on x86_64,
so frames are rendered ahead of the time bar's position and kept in a
small LRU of textures (7.6 MB each) instead of all at once
(docs/radar-architecture.md, memory and bandwidth budget).
"""
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from gi.repository import GLib

from cirro import colors, projection
from cirro.radar_layer import rgba_texture

log = logging.getLogger(__name__)

CAPACITY = 8


@dataclass(frozen=True)
class Rendered:
    texture: object            # Gdk.Texture
    bounds: tuple              # (north, west, south, east) in degrees


class FrameRenderer:
    def __init__(self, on_ready, capacity=CAPACITY):
        """`on_ready(name)` is called on the main thread when the frame of
        that member name has been rendered."""
        self._on_ready = on_ready
        self._capacity = capacity
        self._cache = OrderedDict()   # member name → Rendered
        self._queue = []              # entries still to render, by priority
        self._wanted = set()
        self._reprojections = {}      # Grid → Reprojection
        self._cond = threading.Condition()
        threading.Thread(target=self._worker, daemon=True).start()

    def get(self, entry):
        """The rendered frame, or None if it is not ready."""
        with self._cond:
            rendered = self._cache.get(entry.name)
            if rendered:
                self._cache.move_to_end(entry.name)
            return rendered

    def request(self, entries):
        """Render these entries, the first one first; replaces any earlier
        request that has not been rendered yet."""
        entries = entries[:self._capacity]
        with self._cond:
            self._wanted = {e.name for e in entries}
            self._queue = [e for e in entries if e.name not in self._cache]
            self._cond.notify()

    def _worker(self):
        while True:
            with self._cond:
                while not self._queue:
                    self._cond.wait()
                entry = self._queue.pop(0)
            try:
                rendered = self._render(entry)
            except Exception:
                log.exception("cannot render %s", entry.name)
                continue
            with self._cond:
                self._cache[entry.name] = rendered
                self._evict()
            GLib.idle_add(self._on_ready, entry.name)

    def _evict(self):
        while len(self._cache) > self._capacity:
            # Oldest frame that is not part of the current request.
            name = next((n for n in self._cache if n not in self._wanted),
                        next(iter(self._cache)))
            del self._cache[name]

    def _render(self, entry):
        started = time.monotonic()
        frame = entry.decode()
        decoded = time.monotonic()
        reprojection = self._reprojections.get(frame.grid)
        if reprojection is None:
            reprojection = projection.reproject_grid(frame.grid)
            self._reprojections = {frame.grid: reprojection}
            log.debug("index table in %.2f s", time.monotonic() - decoded)
            decoded = time.monotonic()
        image = colors.colorize(frame, reprojection)
        texture = rgba_texture(image)
        r = reprojection
        log.debug("%s: decoded in %.0f ms, coloured in %.0f ms", entry.name,
                  (decoded - started) * 1000, (time.monotonic() - decoded) * 1000)
        return Rendered(texture, (r.north, r.west, r.south, r.east))
