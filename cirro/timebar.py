"""Time bar below the map: scrub through the frames, play/pause, a "Now"
mark and forecast labelling (docs/radar-architecture.md, TimeBar)."""
from gi.repository import GLib, GObject, Gtk, Pango

# Playback speed and the pause at the end before it loops.
FRAME_MS = 400
END_PAUSE_FRAMES = 3


def _local(time_):
    return GLib.DateTime.new_from_unix_utc(int(time_.timestamp())).to_local()


def clock(time_):
    return _local(time_).format("%H:%M")


def describe(entry, analysis_time):
    """Second line of the label: what the selected frame is."""
    minutes = round((entry.valid_time - analysis_time).total_seconds() / 60)
    if entry.forecast:
        return f"Forecast +{minutes} min"
    if minutes == 0:
        return "Now"
    return f"{-minutes} min ago"


class TimeBar(Gtk.Box):
    """Emits `selected` with the index of the frame to show."""

    __gsignals__ = {
        "selected": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self, ready=lambda index: True):
        """`ready(index)` tells playback whether the next frame can be
        shown yet; playback waits for it instead of skipping frames."""
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_start=6, margin_end=12, margin_top=6)
        self._ready = ready
        self._entries = []
        self._analysis_time = None
        self._timer = 0
        self._end_pause = 0

        self._play = Gtk.Button(icon_name="media-playback-start-symbolic",
                                valign=Gtk.Align.CENTER,
                                css_classes=["circular", "flat"])
        self._play.connect("clicked", lambda *_: self.set_playing(not self.playing))
        self._set_play_button(False)
        self.append(self._play)

        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        labels = Gtk.Box(spacing=6, margin_start=10, margin_end=10)
        self._time = Gtk.Label(xalign=0, css_classes=["heading", "numeric"])
        self._kind = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END,
                               css_classes=["dim-label"])
        labels.append(self._time)
        labels.append(self._kind)
        column.append(labels)

        self._adjustment = Gtk.Adjustment(lower=0, upper=0, step_increment=1,
                                          page_increment=6)
        self._scale = Gtk.Scale(adjustment=self._adjustment, draw_value=False,
                                digits=0, round_digits=0, hexpand=True,
                                show_fill_level=True, has_origin=False,
                                restrict_to_fill_level=False)
        self._scale.update_property([Gtk.AccessibleProperty.LABEL],
                                    ["Radar time"])
        self._changed = self._adjustment.connect("value-changed",
                                                 self._on_value_changed)
        column.append(self._scale)
        self.append(column)
        self.set_sensitive(False)
        self._time.set_label("--:--")
        self._kind.set_label("Loading radar…")

    @property
    def index(self):
        return round(self._adjustment.get_value())

    @property
    def playing(self):
        return self._timer != 0

    def set_frames(self, entries, analysis_time):
        """New timeline; keeps the selected time if it is still there,
        otherwise, or if "Now" was selected, selects the current analysis."""
        selected = self._entries[self.index].valid_time if self._entries else None
        if selected == self._analysis_time:
            selected = analysis_time
        self._entries = entries
        self._analysis_time = analysis_time
        times = [e.valid_time for e in entries]
        now = times.index(analysis_time) if analysis_time in times else 0
        index = times.index(selected) if selected in times else now

        self.set_sensitive(bool(entries))
        self._scale.clear_marks()
        for i, entry in enumerate(entries):
            if i == now:
                self._scale.add_mark(i, Gtk.PositionType.BOTTOM, "Now")
            elif _local(entry.valid_time).get_minute() == 0:
                self._scale.add_mark(i, Gtk.PositionType.BOTTOM, None)
        # The measured part of the bar is filled, the forecast is not.
        self._scale.set_fill_level(now)
        with GObject.signal_handler_block(self._adjustment, self._changed):
            self._adjustment.set_upper(max(0, len(entries) - 1))
            self._adjustment.set_value(index)
        self._update(emit=True)

    def set_playing(self, playing):
        if playing == self.playing or (playing and len(self._entries) < 2):
            return
        if playing:
            if self.index == len(self._entries) - 1:
                self._adjustment.set_value(0)
            self._end_pause = 0
            self._timer = GLib.timeout_add(FRAME_MS, self._on_tick)
        else:
            GLib.source_remove(self._timer)
            self._timer = 0
        self._set_play_button(playing)

    def _set_play_button(self, playing):
        label = "Pause" if playing else "Play"
        self._play.set_icon_name("media-playback-pause-symbolic" if playing
                                 else "media-playback-start-symbolic")
        self._play.set_tooltip_text(label)
        self._play.update_property([Gtk.AccessibleProperty.LABEL], [label])

    def _on_tick(self):
        last = len(self._entries) - 1
        if self.index >= last:
            # Hold the last frame for a moment, then loop.
            self._end_pause += 1
            if self._end_pause >= END_PAUSE_FRAMES:
                self._end_pause = 0
                self._adjustment.set_value(0)
        elif self._ready(self.index + 1):
            self._adjustment.set_value(self.index + 1)
        return GLib.SOURCE_CONTINUE

    def _on_value_changed(self, adjustment):
        # Snap to whole frames while dragging.
        if adjustment.get_value() != self.index:
            adjustment.set_value(self.index)
            return
        self._update(emit=True)

    def _update(self, emit):
        if not self._entries:
            return
        entry = self._entries[self.index]
        text = describe(entry, self._analysis_time)
        self._time.set_label(clock(entry.valid_time))
        self._kind.set_label(text)
        self._scale.update_property([Gtk.AccessibleProperty.VALUE_TEXT],
                                    [f"{clock(entry.valid_time)}, {text}"])
        if emit:
            self.emit("selected", self.index)
