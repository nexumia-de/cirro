"""Station measurements drawn on the map by Cirro (issues #58, #71):
wind as an arrow pointing where the wind blows, with its Beaufort
force; other values as a number. OSD style (light text on a dark
pill), like the pins; labels that would overlap are left out."""
import math

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Shumate", "1.0")
from gi.repository import Gdk, Graphene, Gsk, Shumate  # noqa: E402

from cirro import wind  # noqa: E402



def _rgba(text):
    # Gdk.RGBA(red=…) silently ignores its arguments in PyGObject.
    colour = Gdk.RGBA()
    colour.parse(text)
    return colour


PILL = _rgba("rgba(0, 0, 0, 0.65)")
INK = _rgba("white")
PAD = 3
ARROW = 11    # half length of the arrow in px


# Free space kept around each label, so the map stays readable.
GAP = 10


def _overlaps(box, boxes):
    x, y, w, h = box
    x, y, w, h = x - GAP, y - GAP, w + 2 * GAP, h + 2 * GAP
    return any(x < bx + bw and bx < x + w and y < by + bh and by < y + h
               for bx, by, bw, bh in boxes)


class StationLayer(Shumate.Layer):
    def __init__(self, viewport, kind, unit="", decimals=0):
        """`kind` is "wind" (arrows) or "value" (numbers with `unit`)."""
        super().__init__(viewport=viewport)
        self.set_can_target(False)
        self._kind = kind
        self._unit = unit
        self._decimals = decimals
        self._stations = []
        for prop in ("latitude", "longitude", "zoom-level", "rotation"):
            viewport.connect(f"notify::{prop}", lambda *_: self.queue_draw())

    def set_stations(self, stations):
        self._stations = list(stations)
        self.queue_draw()

    def _text(self, station):
        if self._kind == "wind":
            force = wind.beaufort(station.value)
            return f"{force}"
        return f"{station.value:.{self._decimals}f}{self._unit}"

    def do_snapshot(self, snapshot):
        viewport = self.get_viewport()
        width, height = self.get_width(), self.get_height()
        placed = []
        for station in self._stations:
            x, y = viewport.location_to_widget_coords(
                self, station.latitude, station.longitude)
            if not (-20 <= x <= width + 20 and -20 <= y <= height + 20):
                continue
            layout = self.create_pango_layout(self._text(station))
            tw, th = layout.get_pixel_size()
            arrow = self._kind == "wind" and station.direction is not None \
                and wind.beaufort(station.value) > 0
            w = tw + 2 * PAD + (2 * ARROW + 2 if arrow else 0)
            h = max(th, 2 * ARROW if arrow else 0) + 2 * PAD
            box = (x - w / 2, y - h / 2, w, h)
            if _overlaps(box, placed):
                continue
            placed.append(box)
            rect = Graphene.Rect().init(*box)
            rounded = Gsk.RoundedRect()
            rounded.init_from_rect(rect, h / 2)
            snapshot.push_rounded_clip(rounded)
            snapshot.append_color(PILL, rect)
            snapshot.pop()
            left = box[0] + PAD
            if arrow:
                self._arrow(snapshot, left + ARROW, y, station.direction)
                left += 2 * ARROW + 2
            snapshot.save()
            snapshot.translate(Graphene.Point().init(left, y - th / 2))
            snapshot.append_layout(layout, INK)
            snapshot.restore()

    def _arrow(self, snapshot, cx, cy, direction):
        """Arrow through (cx, cy) pointing where the wind blows: the
        opposite of `direction` (where it comes from)."""
        angle = math.radians(direction + 180)
        dx, dy = math.sin(angle), -math.cos(angle)
        tip = (cx + dx * ARROW, cy + dy * ARROW)
        tail = (cx - dx * ARROW, cy - dy * ARROW)
        builder = Gsk.PathBuilder.new()
        builder.move_to(*tail)
        builder.line_to(*tip)
        for side in (-1, 1):
            a = angle + math.pi + side * 0.5
            builder.move_to(*tip)
            builder.line_to(tip[0] + math.sin(a) * 6, tip[1] - math.cos(a) * 6)
        stroke = Gsk.Stroke.new(1.8)
        stroke.set_line_cap(Gsk.LineCap.ROUND)
        snapshot.append_stroke(builder.to_path(), stroke, INK)
