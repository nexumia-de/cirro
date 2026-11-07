"""The short rain status of every place for the places list (issue
#56): "Rain in 35 min", "Raining, stops in 25 min", "Dry for 2 h".
All places are sampled in one pass over the frames in a worker thread,
again when a new analysis arrives or the places change."""
import threading

from gi.repository import GLib

from cirro import nowcast


class PlacesRain:
    def __init__(self, store, callback):
        """`callback({place id: text})` on the main thread."""
        self._store = store
        self._callback = callback
        self._entries = []
        self._analysis_time = None
        self._generation = 0
        store.connect("changed", lambda *_: self._start())

    def set_frames(self, entries, analysis_time):
        self._entries = list(entries)
        self._analysis_time = analysis_time
        self._start()

    def _start(self):
        self._generation += 1
        if not self._entries:
            return
        model = self._store.model
        places = [model.get_item(i) for i in range(model.get_n_items())]
        places = [p for p in places if p.has_position]
        ids = [p.id for p in places]
        points = [(round(p.latitude, 3), round(p.longitude, 3)) for p in places]
        generation = self._generation
        entries, analysis_time = self._entries, self._analysis_time

        def work():
            series = nowcast.series_many(
                entries, analysis_time, points,
                cancelled=lambda: generation != self._generation)
            if series is None:
                return
            texts = {i: nowcast.short(values) for i, values in zip(ids, series)}
            GLib.idle_add(self._done, generation, texts)

        threading.Thread(target=work, name="places-rain", daemon=True).start()

    def _done(self, generation, texts):
        if generation == self._generation:
            self._callback(texts)
        return GLib.SOURCE_REMOVE
