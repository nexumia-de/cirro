"""One shown map layer: its time steps, and the image for the visible
area and the selected time, drawn by a texture layer on the map.

Images are fetched in worker threads, kept as textures in memory (a
small LRU) and as PNG on disk (cirro/layers/cache.py). Capabilities are
refreshed while the layer is shown, so the time steps move on."""
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, GObject  # noqa: E402

from cirro.layers import wms  # noqa: E402
from cirro.layers.timeaxis import latest_at, parse_time  # noqa: E402
from cirro.radar_layer import RadarLayer  # noqa: E402

log = logging.getLogger(__name__)

MEMORY = 48
# Timeless layers (warnings) are fetched again after this long.
TIMELESS_TTL = timedelta(minutes=5)


def refresh_after(axis):
    """How often the time steps are read again: often for nowcasts."""
    if axis is None:
        return timedelta(minutes=5)
    return timedelta(minutes=5) if axis.step <= timedelta(minutes=15) \
        else timedelta(minutes=30)


class LayerView(GObject.Object):
    """`steps-changed` when the time steps changed; `image` when an image
    arrived (to check readiness while playing); `failed` with a message."""

    __gsignals__ = {
        "steps-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "image": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, layer, variant_index, viewport, cache, executor):
        super().__init__()
        self.layer = layer
        self.variant_index = variant_index
        self.variant = layer.variant(variant_index)
        self._cache = cache
        self._executor = executor
        self.drawing = RadarLayer(viewport)
        self.drawing.set_opacity(layer.alpha)
        self.caps = None
        self.steps = []
        self._known = False   # steps-changed was emitted once
        self._missing = set()  # steps the server had no data for
        self._time = None
        self._view = None
        self._memory = OrderedDict()   # url → (texture, bounds, fetched at)
        self._pending = set()
        self._time_of = {}     # url → its time step
        self._failed = False
        self._closed = False
        self._timer = 0
        self._shown_url = None
        self._load_capabilities()

    @property
    def name(self):
        return self.variant.wms[0]

    @property
    def timeless(self):
        return self.caps is not None and self.caps.axis is None

    # Time steps

    def _load_capabilities(self):
        future = self._executor.submit(wms.fetch_capabilities, self.name)
        future.add_done_callback(
            lambda f: GLib.idle_add(self._on_capabilities, f))

    def _on_capabilities(self, future):
        if self._closed:
            return GLib.SOURCE_REMOVE
        try:
            self.caps = future.result()
        except Exception as error:   # network, parsing
            log.warning("%s: capabilities: %s", self.name, error)
            self._fail(str(error))
            self._schedule(timedelta(minutes=1))
            return GLib.SOURCE_REMOVE
        self._update_steps()
        self._schedule(refresh_after(self.caps.axis))
        self._show()
        return GLib.SOURCE_REMOVE

    def _schedule(self, delay):
        if self._timer:
            GLib.source_remove(self._timer)
        self._timer = GLib.timeout_add_seconds(int(delay.total_seconds()),
                                               self._on_timer)

    def _on_timer(self):
        self._timer = 0
        if self.timeless:
            self._memory.clear()
        self._load_capabilities()
        return GLib.SOURCE_REMOVE

    def _update_steps(self, now=None):
        now = now or datetime.now(timezone.utc)
        axis = self.caps.axis
        if axis is None:
            steps = []
        else:
            first = now - self.layer.past - axis.step
            steps = axis.times(first, axis.last or now)
            if not steps and axis.last:
                steps = axis.times(axis.last - axis.step * 24, axis.last)
            steps = usable(steps, self.caps.reference_time, self.variant)
            steps = [t for t in steps if t not in self._missing]
        if steps != self.steps or not self._known:
            self._known = True
            self.steps = steps
            self.emit("steps-changed")

    def now_index(self, now=None):
        return latest_at(self.steps, now or datetime.now(timezone.utc))

    def nearest(self, time_):
        """The step to show for a time of the base layer: the nearest one,
        if it is close enough (half a step of either layer, at least
        10 min); None hides the layer."""
        if self.caps is None or self.caps.axis is None or not self.steps \
                or time_ is None:
            return None
        # Only the layer's own window: the server does not keep every
        # time it advertises (docs/data-sources.md, section 11).
        tolerance = max(self.caps.axis.step / 2, timedelta(minutes=10))
        best = min(self.steps, key=lambda t: abs(t - time_))
        return best if abs(best - time_) <= tolerance else None

    # Images

    @property
    def time(self):
        return self._time

    def set_time(self, time_):
        self._time = time_
        self._show()

    def set_view(self, view):
        self._view = view
        self._show()

    def _url(self, time_, view):
        url = wms.map_url(self.variant.wms, view.bbox, view.size,
                           None if self.timeless else time_,
                           self.variant.style, self.variant.cql,
                           self.caps.reference_time)
        if time_ is not None:
            self._time_of[url] = time_
        return url

    def _wanted(self):
        """URL of the image to show now, or None."""
        if self.caps is None or self._view is None:
            return None
        if not self.timeless and self._time is None:
            return None
        return self._url(self._time, self._view)

    def _show(self):
        url = self._wanted()
        if url is None:
            if self.caps is not None and not self.timeless:
                self.drawing.set_visible(False)
            return
        self.drawing.set_visible(True)
        hit = self._memory.get(url)
        if hit and self.timeless and \
                datetime.now(timezone.utc) - hit[2] > TIMELESS_TTL:
            hit = None
        if hit:
            self._memory.move_to_end(url)
            if url != self._shown_url:
                self._shown_url = url
                self.drawing.set_frame(hit[0], hit[1])
            return
        self._request(url, self._view)

    def ready(self, time_):
        if self.caps is None or self._view is None:
            return False
        return self._url(time_, self._view) in self._memory

    def prefetch(self, times):
        if self.caps is None or self._view is None or self.timeless:
            return
        for time_ in times:
            url = self._url(time_, self._view)
            if url not in self._memory:
                self._request(url, self._view)

    def _request(self, url, view):
        if url in self._pending:
            return
        self._pending.add(url)
        cacheable = not self.timeless
        future = self._executor.submit(_load, url, self._cache if cacheable else None)
        future.add_done_callback(
            lambda f: GLib.idle_add(self._on_image, url, view, f))

    def _on_image(self, url, view, future):
        self._pending.discard(url)
        if self._closed:
            return GLib.SOURCE_REMOVE
        try:
            texture = future.result()
        except Exception as error:
            log.warning("%s: image: %s", self.name, error)
            time_ = self._time_of.pop(url, None)
            if "No data available" in str(error) and time_ is not None:
                # The axis promised a step the server can't draw: drop it.
                self._missing.add(time_)
                self._update_steps()
                return GLib.SOURCE_REMOVE
            if url == self._wanted():
                self._fail(str(error))
            return GLib.SOURCE_REMOVE
        self._failed = False
        self._memory[url] = (texture, view.bounds, datetime.now(timezone.utc))
        while len(self._memory) > MEMORY:
            self._memory.popitem(last=False)
        if url == self._wanted():
            self._show()
        self.emit("image")
        return GLib.SOURCE_REMOVE

    def _fail(self, message):
        if not self._failed:
            self._failed = True
            self.emit("failed", message)

    def retry(self):
        self._failed = False
        if self.caps is None:
            self._load_capabilities()
        else:
            self._show()

    def close(self):
        self._closed = True
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        self._memory.clear()


def usable(steps, reference_time, variant):
    """Steps a forecast sum has data for: `variant.lead` after the model
    run, then every `variant.every`."""
    if not reference_time or (not variant.lead and not variant.every):
        return steps
    run = parse_time(reference_time)
    out = []
    for time_ in steps:
        lead = time_ - run
        if lead < variant.lead:
            continue
        if variant.every and lead % variant.every:
            continue
        out.append(time_)
    return out


def _load(url, cache):
    """Worker thread: PNG from the disk cache or the server → texture."""
    data = cache.get(url) if cache else None
    if data is None:
        data = wms.fetch_map(url)
        if cache:
            cache.put(url, data)
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
