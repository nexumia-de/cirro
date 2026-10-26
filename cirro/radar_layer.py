import math

import gi

gi.require_version("Gsk", "4.0")
gi.require_version("Shumate", "1.0")
from gi.repository import Gdk, GLib, Graphene, Gsk, Shumate  # noqa: E402

# From this zoom on, radar cells are several pixels wide: draw them crisp.
NEAREST_ZOOM = 9


def rgba_texture(image):
    """(height, width, 4) uint8 array → Gdk.Texture."""
    height, width, _ = image.shape
    return Gdk.MemoryTexture.new(width, height, Gdk.MemoryFormat.R8G8B8A8,
                                 GLib.Bytes.new(image.tobytes()), width * 4)


class RadarLayer(Shumate.Layer):
    """Draws one Mercator-aligned radar texture at its geographic bounds,
    or a crossfade of two (smooth playback).

    Switching frames only swaps texture references; the crossfade is a
    GSK cross-fade node, so no pixels are touched in Python
    (docs/radar-architecture.md).
    """

    def __init__(self, viewport):
        super().__init__(viewport=viewport)
        self.set_can_target(False)
        self._texture = None
        self._bounds = None
        self._next = None
        self._fraction = 0.0
        for prop in ("latitude", "longitude", "zoom-level", "rotation"):
            viewport.connect(f"notify::{prop}", lambda *_: self.queue_draw())

    def set_frame(self, texture, bounds, next_texture=None, fraction=0.0):
        """`bounds` is (north, west, south, east) in degrees. With
        `next_texture` (same bounds), draws `texture` faded into it by
        `fraction` (0 … 1)."""
        if not next_texture:
            fraction = 0.0
        state = (texture, bounds, next_texture if fraction else None, fraction)
        if state == (self._texture, self._bounds, self._next, self._fraction):
            return
        self._texture, self._bounds, self._next, self._fraction = state
        self.queue_draw()

    def do_snapshot(self, snapshot):
        viewport = self.get_viewport()
        source = viewport.get_reference_map_source()
        if self._texture is None or source is None:
            return
        north, west, south, east = self._bounds
        zoom = viewport.get_zoom_level()
        width, height = self.get_width(), self.get_height()
        # Same arithmetic as shumate_viewport_location_to_widget_coords(),
        # without the rotation, which is applied to the whole snapshot.
        left = width / 2 - source.get_x(zoom, viewport.get_longitude())
        top = height / 2 - source.get_y(zoom, viewport.get_latitude())
        x0 = left + source.get_x(zoom, west)
        y0 = top + source.get_y(zoom, north)
        rect = Graphene.Rect().init(x0, y0, left + source.get_x(zoom, east) - x0,
                                    top + source.get_y(zoom, south) - y0)

        rotation = viewport.get_rotation()
        if rotation:
            snapshot.save()
            center = Graphene.Point().init(width / 2, height / 2)
            snapshot.translate(center)
            snapshot.rotate(math.degrees(rotation))
            snapshot.translate(Graphene.Point().init(-width / 2, -height / 2))
        scaling = Gsk.ScalingFilter.NEAREST if zoom >= NEAREST_ZOOM \
            else Gsk.ScalingFilter.LINEAR
        if self._next is not None:
            snapshot.push_cross_fade(self._fraction)
            snapshot.append_scaled_texture(self._texture, scaling, rect)
            snapshot.pop()
            snapshot.append_scaled_texture(self._next, scaling, rect)
            snapshot.pop()
        else:
            snapshot.append_scaled_texture(self._texture, scaling, rect)
        if rotation:
            snapshot.restore()
