"""One radar source for the window that switches between providers by
the selected place: DWD's RV, or DMI's composite in Denmark (issue #11).
It forwards the API of RadarSource (store, loading, stale, changed,
failed, start, set_active, refresh, set_metered) to the current one."""

from typing import Any

from gi.repository import GObject

ATTRIBUTION = {
    "dwd": "Based on data from Deutscher Wetterdienst",
    "dmi": "Radar: DMI, converted to rain rates (CC BY 4.0)",
}


class SourceSwitch(GObject.Object):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
    }

    loading = GObject.Property(type=bool, default=False)
    stale = GObject.Property(type=bool, default=False)
    provider = GObject.Property(type=str, default="dwd")

    def __init__(self, sources):
        """`sources`: {provider name: source or a function making one}."""
        super().__init__()
        self._sources = dict(sources)
        self._started = set()
        self._active = False
        self._metered = False
        self._handlers: list[int] = []
        self._current: Any = self._get("dwd")
        self._use("dwd", first=True)

    @property
    def store(self):
        return self._current.store

    def _get(self, name):
        source = self._sources[name]
        if callable(source) and not isinstance(source, GObject.Object):
            source = self._sources[name] = source()
        return source

    def _use(self, name, first=False):
        old = None if first else self._current
        if old is not None:
            for handler in self._handlers:
                old.disconnect(handler)
            old.set_active(False)
        self._current = source = self._get(name)
        self._handlers = [
            source.connect("changed", lambda *_: self.emit("changed")),
            source.connect("failed", lambda _s, m, show: self.emit("failed", m, show)),
            source.connect("notify::loading", lambda *_: self._sync()),
            source.connect("notify::stale", lambda *_: self._sync()),
        ]
        source.set_metered(self._metered)
        self.provider = name
        self._sync()
        if old is not None:
            self.start()
            source.set_active(self._active)
            self.emit("changed")

    def _sync(self):
        self.loading = self._current.loading
        self.stale = self._current.stale

    def set_provider(self, name):
        if name in self._sources and name != self.provider:
            self._use(name)

    def start(self):
        if self.provider not in self._started:
            self._started.add(self.provider)
            self._current.start()

    def set_active(self, active):
        self._active = active
        self._current.set_active(active)

    def set_metered(self, metered):
        self._metered = metered
        self._current.set_metered(metered)

    def refresh(self):
        self._current.refresh()
