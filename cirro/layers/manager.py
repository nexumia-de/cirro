"""The map layers shown at a time: one base layer (the radar, or a DWD
layer with its own time steps) and any number of overlays, which follow
the base layer's time. Keeps the map's source note in step with them
and remembers the choice (docs/map-layers.md)."""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from gi.repository import GLib, GObject

from cirro.layers import catalogue, geometry, info, legend_data, settings, wms
from cirro.layers.cache import ImageCache
from cirro.layers.view import LayerView
from cirro.timebar import clock

log = logging.getLogger(__name__)

SOURCE_NOTE = "Based on data from Deutscher Wetterdienst"
# Map moves settle for this long before new images are requested.
DEBOUNCE_MS = 300
# Steps fetched ahead of the selected one, for playback.
PREFETCH = 4


@dataclass(frozen=True)
class Step:
    """A time bar entry of a DWD base layer (cirro/timebar.py)."""
    valid_time: datetime
    forecast: bool


class LayerManager(GObject.Object):
    """`changed` when the base layer or its time steps changed (the time
    bar is set up again); `legend` when the base layer's legend is known
    (None: the radar's own, or none); `ready` when an image arrived;
    `failed` with the layer title."""

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "legend": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "ready": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, simple_map, radar_layer, pins, persist=True):
        """`persist`: read and save the choice (not with recorded demo
        data, which screenshots use)."""
        super().__init__()
        self._map = simple_map.get_map()
        self._license = simple_map.get_license()
        self._viewport = simple_map.get_viewport()
        self._radar_layer = radar_layer
        self._pins = pins
        self._executor = ThreadPoolExecutor(max_workers=4,
                                            thread_name_prefix="layers")
        self._cache = ImageCache()
        self._legends = {}
        self._debounce = 0
        self._persist = persist
        self.base_id, self.base_variant, overlays = \
            settings.load() if persist else (catalogue.RADAR, 0, {})
        self.base = None          # LayerView of a DWD base layer
        self.overlays = {}        # id → LayerView
        self._time = None
        for prop in ("latitude", "longitude", "zoom-level", "rotation"):
            self._viewport.connect(f"notify::{prop}", self._on_moved)
        self._set_base(self.base_id, self.base_variant, save=False)
        for layer_id, variant in overlays.items():
            self.set_overlay(layer_id, True, variant, save=False)
        self._update_credits()

    # Choice

    @property
    def radar(self):
        return self.base_id == catalogue.RADAR

    def set_base(self, layer_id, variant=0):
        self._set_base(layer_id, variant)

    def _set_base(self, layer_id, variant, save=True):
        if self.base is not None:
            self._drop(self.base)
            self.base = None
        layer = catalogue.get(layer_id)
        if layer is None or layer.role != catalogue.BASE:
            layer_id, variant = catalogue.RADAR, 0
        self.base_id, self.base_variant = layer_id, variant
        self._radar_layer.set_visible(self.radar)
        if not self.radar:
            self.base = self._add(layer, variant, behind=self._radar_layer)
            self.base.connect("steps-changed", lambda *_: self.emit("changed"))
        self._load_legend()
        self._update_credits()
        if save:
            self._save()
        self.emit("changed")

    def set_overlay(self, layer_id, enabled, variant=0, save=True):
        layer = catalogue.get(layer_id)
        if layer is None or layer.role != catalogue.OVERLAY:
            return
        old = self.overlays.pop(layer_id, None)
        if old is not None:
            self._drop(old)
        if enabled:
            view = self._add(layer, variant, behind=self._pins)
            view.connect("steps-changed", lambda v: self._follow_one(v))
            self.overlays[layer_id] = view
            self._follow_one(view)
        self._update_credits()
        if save:
            self._save()

    def _save(self):
        if not self._persist:
            return
        settings.save(self.base_id, self.base_variant,
                      {k: v.variant_index for k, v in self.overlays.items()})

    def _add(self, layer, variant, behind):
        view = LayerView(layer, variant, self._viewport, self._cache,
                         self._executor)
        self._map.insert_layer_behind(view.drawing, behind)
        view.connect("failed", lambda v, message: self.emit("failed", v.layer.title))
        view.connect("image", lambda *_: self.emit("ready"))
        geometry_view = self._current_view()
        if geometry_view:
            view.set_view(geometry_view)
        return view

    def _drop(self, view):
        view.close()
        self._map.remove_layer(view.drawing)

    def views(self):
        return ([self.base] if self.base else []) + list(self.overlays.values())

    # Time

    def steps(self):
        """(time bar entries, the "now" time) of the DWD base layer."""
        if self.base is None or not self.base.steps:
            return [], None
        now = datetime.now(timezone.utc)
        steps = [Step(t, t > now) for t in self.base.steps]
        return steps, self.base.steps[self.base.now_index(now)]

    @property
    def daily(self):
        axis = self.base.caps.axis if self.base and self.base.caps else None
        return axis is not None and axis.step >= timedelta(days=1)

    def show(self, index):
        """Show step `index` of the DWD base layer (and overlays at it)."""
        if self.base is None or not self.base.steps:
            return
        index = min(max(index, 0), len(self.base.steps) - 1)
        self.base.set_time(self.base.steps[index])
        self.base.prefetch(self.base.steps[index + 1:index + 1 + PREFETCH])
        self.follow(self.base.steps[index])

    def ready(self, index):
        if self.base is None or not self.base.steps:
            return True
        index = min(max(index, 0), len(self.base.steps) - 1)
        return self.base.ready(self.base.steps[index])

    def follow(self, time_):
        """Overlays at the time the base layer shows."""
        self._time = time_
        for view in self.overlays.values():
            self._follow_one(view)

    def _follow_one(self, view):
        if view.caps is None:
            return
        if view.timeless:
            view.set_time(None)
            return
        if self._time is None:
            return
        view.set_time(view.nearest(self._time))

    # Map area

    def _current_view(self):
        width, height = self._map.get_width(), self._map.get_height()
        if width <= 1 or height <= 1:
            return None
        return geometry.view(self._viewport.get_latitude(),
                             self._viewport.get_longitude(),
                             self._viewport.get_zoom_level(), width, height,
                             self._map.get_scale_factor(),
                             self._viewport.get_rotation())

    def _on_moved(self, *_):
        if self._debounce:
            GLib.source_remove(self._debounce)
        self._debounce = GLib.timeout_add(DEBOUNCE_MS, self._apply_view)

    def _apply_view(self):
        self._debounce = 0
        view = self._current_view()
        if view:
            for layer_view in self.views():
                layer_view.set_view(view)
        return GLib.SOURCE_REMOVE

    def resized(self, *_):
        """The window changed size (GTK widgets don't notify their own)."""
        self._on_moved()

    def retry(self):
        for view in self.views():
            view.retry()

    # Source note, legend, value at a point

    def _update_credits(self):
        credits = []
        for view in self.views():
            for credit in view.layer.credits:
                if credit not in credits:
                    credits.append(credit)
        self._license.set_extra_text(" · ".join([SOURCE_NOTE] + credits))

    def _load_legend(self):
        if self.radar:
            self.emit("legend", None)
            return
        layer, variant = self.base.layer, self.base.variant
        key = (variant.wms[0], variant.style)
        if key in self._legends:
            self.emit("legend", self._legends[key])
            return
        self.emit("legend", None)
        future = self._executor.submit(wms.fetch_legend, variant.wms[0],
                                       variant.style)

        def done(f):
            try:
                legend = legend_data.parse(f.result(), layer.legend)
            except Exception as error:
                log.warning("%s: legend: %s", variant.wms[0], error)
                legend = None
            if legend and layer.unit:
                legend = legend_data.Legend(legend.kind, legend.entries, layer.unit)
            self._legends[key] = legend
            if self.base is not None and self.base.variant == variant:
                self.emit("legend", legend)
            return GLib.SOURCE_REMOVE
        future.add_done_callback(lambda f: GLib.idle_add(done, f))

    def value_at(self, latitude, longitude, callback, limit=2):
        """callback(text) for each of up to `limit` shown layers that can
        tell their value under a point, the base layer first. Returns
        whether any was asked."""
        asked = 0
        for view in self.views():
            if asked >= limit:
                break
            if view.layer.value is None or view.caps is None:
                continue
            time_ = None if view.timeless else view.time
            if not view.timeless and time_ is None:
                continue
            url = wms.feature_info_url(view.variant.wms, latitude, longitude,
                                       time_, view.variant.cql,
                                       view.caps.reference_time,
                                       view.layer.value.fields)
            future = self._executor.submit(wms.fetch_feature_info, url)
            future.add_done_callback(lambda f, layer=view.layer, t=time_: GLib.idle_add(
                self._value_done, f, layer, t, callback))
            asked += 1
        return asked > 0

    def _value_done(self, future, layer, time_, callback):
        try:
            text = info.describe(layer.value, future.result())
        except Exception as error:
            log.warning("%s: value: %s", layer.id, error)
            text = None
        if text:
            when = f" · {clock(time_)}" if time_ is not None else ""
            callback(f"{layer.title}: {text}{when}")
        return GLib.SOURCE_REMOVE
