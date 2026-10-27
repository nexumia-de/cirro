"""Point nowcast below the map: a sentence and a 2-hour bar chart of the
rain rate at the selected place (docs/nowcast.md)."""
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Graphene, Gtk  # noqa: E402

from cirro import colors, nowcast  # noqa: E402
from cirro.timebar import clock  # noqa: E402

# Time axis of the chart, in minutes relative to the analysis time.
FIRST, LAST, STEP = -60, 120, 5
# Guide lines with their rate in mm/h.
GUIDES = (1, 10)


def _rgba(rgb):
    colour = Gdk.RGBA()
    colour.red, colour.green, colour.blue = (c / 255 for c in rgb)
    colour.alpha = 1.0
    return colour


class NowcastChart(Gtk.Widget):
    """One bar per 5-min frame, height on a log scale of the rain rate,
    coloured like the map. Chrome (axis, labels, "Now" line) uses the
    widget's foreground colour, so it follows light, dark and high
    contrast. Drawn with GtkSnapshot, which needs no pycairo."""

    HEIGHT = 72

    def __init__(self):
        super().__init__(hexpand=True, accessible_role=Gtk.AccessibleRole.IMG,
                         css_classes=["caption", "numeric"])
        self.update_property(
            [Gtk.AccessibleProperty.LABEL],
            ["Rain rate from one hour ago to two hours ahead"])
        self._values = []

    def set_values(self, values):
        self._values = values or []
        self.queue_draw()

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.VERTICAL:
            return self.HEIGHT, self.HEIGHT, -1, -1
        return 0, 0, -1, -1

    def _layout(self, text):
        layout = self.create_pango_layout(text)
        width, height = layout.get_pixel_size()
        return layout, width, height

    def do_snapshot(self, snapshot):
        width, height = self.get_width(), self.get_height()
        fg = self.get_color()

        def ink(alpha):
            colour = fg.copy()
            colour.alpha = fg.alpha * alpha
            return colour

        def rect(colour, x, y, w, h):
            snapshot.append_color(colour, Graphene.Rect().init(x, y, w, h))

        def text(layout, colour, x, y):
            snapshot.save()
            snapshot.translate(Graphene.Point().init(x, y))
            snapshot.append_layout(layout, colour)
            snapshot.restore()

        # Left gutter for the guide labels, bottom row for the time axis.
        labels = [self._layout(str(g)) for g in GUIDES]
        gutter = max(w for _, w, _ in labels) + 4
        axis_h = self._layout("Now")[2]
        top, bottom = 1, height - axis_h - 2
        plot = bottom - top
        slot = (width - gutter) / ((LAST - FIRST) // STEP + 1)

        def x_of(minutes):
            return gutter + (minutes - FIRST) / STEP * slot

        for (layout, _, h), rate in zip(labels, GUIDES):
            y = round(bottom - nowcast.bar_height(rate) * plot)
            rect(ink(0.15), gutter, y, width - gutter, 1)
            text(layout, ink(0.55), 0, y - h / 2)

        bar = max(1.0, slot * 0.7)
        for value in self._values:
            colour = colors.rgb(value.rate)
            if colour is None or not FIRST <= value.minutes <= LAST:
                continue
            h = max(1.0, nowcast.bar_height(value.rate) * plot)
            rect(_rgba(colour), x_of(value.minutes) + (slot - bar) / 2, bottom - h, bar, h)

        rect(ink(0.35), gutter, bottom, width - gutter, 1)

        # "Now" line and label, then the full local hours where they fit.
        now_x = x_of(0) + slot / 2
        rect(ink(0.8), round(now_x), top, 1, bottom + 2 - top)
        taken = []
        ticks = [(now_x, "Now")]
        for value in self._values:
            if value.minutes != 0 and value.valid_time.astimezone().minute == 0:
                ticks.append((x_of(value.minutes) + slot / 2,
                              clock(value.valid_time)))
        for x, label in ticks:
            layout, w, _ = self._layout(label)
            left = min(max(x - w / 2, gutter), width - w)
            if any(left < r + 6 and left + w + 6 > l for l, r in taken):
                continue
            taken.append((left, left + w))
            if label != "Now":
                rect(ink(0.35), round(x), bottom, 1, 3)
            text(layout, ink(1.0 if label == "Now" else 0.55), left, bottom + 2)


class NowcastView(Gtk.Box):
    """Samples the frames at the place in a worker thread (decoding a
    member costs 12–55 ms) and shows the result. `actions` is a widget
    shown next to the place, e.g. its menu."""

    def __init__(self, actions=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_start=12, margin_end=12, margin_top=6)
        row = Gtk.Box(spacing=6)
        self._sentence = Gtk.Label(xalign=0, hexpand=True, wrap=True,
                                   css_classes=["heading"])
        self._place = Gtk.Label(xalign=1, valign=Gtk.Align.BASELINE,
                                css_classes=["caption", "dim-label"])
        row.append(self._sentence)
        row.append(self._place)
        if actions:
            actions.set_valign(Gtk.Align.CENTER)
            row.append(actions)
        self.append(row)
        # The window's breakpoint hides the chart itself; this box hides
        # it while there is nothing to show.
        self.chart = NowcastChart()
        self._chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  visible=False)
        self._chart_box.append(self.chart)
        self.append(self._chart_box)

        self._entries = []
        self._analysis_time = None
        self._point = None
        self._cache = {}
        self._generation = 0
        self.set_place(None)

    def set_frames(self, entries, analysis_time):
        self._entries = list(entries)
        self._analysis_time = analysis_time
        names = {e.name for e in self._entries}
        self._cache = {k: v for k, v in list(self._cache.items())
                       if k[0] in names}
        self._start()

    def set_place(self, position, label=""):
        """Sample at (latitude, longitude), or show a hint without one.
        `label` says what the place is, e.g. "My location"."""
        self._place.set_label(label)
        self._place.set_visible(bool(label))
        point = position and (round(position[0], 3), round(position[1], 3))
        if point == self._point and point:
            return
        self._point = point
        if not point:
            self._generation += 1
            self._sentence.set_label("Tap the map or search for a place")
            self._chart_box.set_visible(False)
            return
        self._start()

    def _start(self):
        self._generation += 1
        if not self._entries or self._point is None:
            return
        generation = self._generation
        entries, analysis_time = self._entries, self._analysis_time
        latitude, longitude = self._point
        cache = self._cache

        def work():
            values = nowcast.series(
                entries, analysis_time, latitude, longitude, cache,
                cancelled=lambda: generation != self._generation)
            if values is not None:
                GLib.idle_add(self._show, generation, values)

        threading.Thread(target=work, name="nowcast", daemon=True).start()

    def _show(self, generation, values):
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        text = nowcast.summary(values) or "No radar data for this place"
        self._sentence.set_label(text)
        self.chart.set_values(values)
        self.chart.update_property([Gtk.AccessibleProperty.DESCRIPTION], [text])
        self._chart_box.set_visible(True)
        return GLib.SOURCE_REMOVE
