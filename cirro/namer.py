"""Looks up the default names of places in a worker thread
(docs/places.md, names). Only when a place is created or moved, never per
frame or pan; offline it retries later, and the place shows its
coordinates meanwhile."""
import logging
import queue
import threading

from gi.repository import GLib

from cirro import geocode
from cirro.places import coordinates

log = logging.getLogger(__name__)

RETRY_SECONDS = 300


class Namer:
    def __init__(self, store, enabled=True):
        self._store = store
        self._enabled = enabled
        self._queue = queue.Queue()
        self._pending = set()
        self._retry = 0
        self._thread = None

    def request(self, place):
        if not self._enabled or not place.has_position or place in self._pending:
            return
        self._pending.add(place)
        self._queue.put((place, place.position))
        if self._thread is None:
            self._thread = threading.Thread(target=self._work, name="namer",
                                            daemon=True)
            self._thread.start()

    def request_unnamed(self):
        for place in self._store.unnamed():
            self.request(place)

    def _work(self):
        while True:
            place, position = self._queue.get()
            try:
                name = geocode.reverse(*position)
            except (OSError, ValueError) as error:
                log.info("no place name for %s: %s", position, error)
                GLib.idle_add(self._failed, place)
                continue
            GLib.idle_add(self._named, place, position, name)

    def _named(self, place, position, name):
        self._pending.discard(place)
        # A place moved in the meantime gets its own lookup.
        if place.position != position:
            self.request(place)
        elif not place.default_name:
            # Nowhere (e.g. at sea): keep the coordinates as the name so
            # that it is not looked up again.
            place.default_name = name or coordinates(*position)
        return GLib.SOURCE_REMOVE

    def _failed(self, place):
        self._pending.discard(place)
        if not self._retry:
            self._retry = GLib.timeout_add_seconds(RETRY_SECONDS, self._on_retry)
        return GLib.SOURCE_REMOVE

    def _on_retry(self):
        self._retry = 0
        self.request_unnamed()
        return GLib.SOURCE_REMOVE
