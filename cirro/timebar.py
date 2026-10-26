"""Time bar below the map: scrub through the frames, play/pause, a "Now"
mark and forecast labelling (docs/radar-architecture.md, TimeBar).

Playback moves a fractional playhead at the display's frame rate; the
map crossfades between the two frames on either side of it
(docs/decisions/smooth-playback.md)."""
import logging
import math

from gi.repository import GLib, GObject, Gsk, Gtk, Pango

log = logging.getLogger(__name__)

# Seconds per 5-min step at normal speed, and the pause at the end (in
# steps) before playback loops.
STEP_SECONDS = 0.4
END_PAUSE_FRAMES = 3
# Playback speeds offered in the main menu: (label, factor).
SPEEDS = (("Slow", 0.5), ("Normal", 1.0), ("Fast", 2.0))
# Playback redraws the radar at most this often. 30 per second looks
# smooth for a crossfade and halves the drawing work of a 60 Hz display.
FPS = 30
# With GTK's software renderer (cairo: no usable GPU) every crossfade is
# blended by the CPU, so update less often (docs/radar-architecture.md,
# measurements).
SOFTWARE_FPS = 10
# A longer gap between two frame clock ticks (a stall, a hidden window)
# does not make the playhead jump.
MAX_TICK_SECONDS = 0.1


def advance(position, frames, count, ready, hold=END_PAUSE_FRAMES):
    """The playhead `frames` (fractional) later on a timeline of `count`
    frames. Past the last frame it holds that frame for `hold` steps, then
    loops to 0. It does not move into a frame that `ready(index)` says is
    not rendered yet: it waits on the frame before it instead."""
    last = count - 1
    target = position + frames
    if target >= last + hold:
        return 0.0
    # Showing a position between i and i + 1 needs frame i + 1.
    for i in range(math.floor(position) + 1, min(math.floor(target) + 1, last) + 1):
        if not ready(i):
            return max(position, float(i - 1))
    return target


def blend(position, count):
    """(index, fraction) to draw for a playhead: frame `index` crossfaded
    into the next one by `fraction` (0 shows `index` alone)."""
    last = count - 1
    index = min(math.floor(position), last)
    return index, (position - index if index < last else 0.0)


def due(elapsed_us, fps=FPS):
    """Whether a frame clock tick `elapsed_us` µs after the last update
    should update again. The 20 % tolerance absorbs tick jitter, so a
    60 Hz clock updates on every second tick, a 120 Hz one on every
    fourth."""
    return elapsed_us >= 0.8e6 / fps


def step_frames(seconds, speed):
    """Frames the playhead moves in `seconds` of frame clock time."""
    return min(seconds, MAX_TICK_SECONDS) * speed / STEP_SECONDS


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
    """Emits `selected` with the index of the frame to show, and while
    playing `blend` with that index and how far (0 … 1) it has faded
    into the next frame."""

    __gsignals__ = {
        "selected": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "blend": (GObject.SignalFlags.RUN_FIRST, None, (int, float)),
    }

    def __init__(self, ready=lambda index: True):
        """`ready(index)` tells playback whether the next frame can be
        shown yet; playback waits for it instead of skipping frames."""
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_start=6, margin_end=12, margin_top=6)
        self._ready = ready
        self._entries = []
        self._analysis_time = None
        self._tick = 0
        self._last_tick = 0
        self._position = 0.0     # playhead in frames, past the end while holding
        self._speed = 1.0
        self._fps = FPS

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
        # Fractional while playing; the frame being faded out.
        return math.floor(self._adjustment.get_value() + 1e-9)

    @property
    def playing(self):
        return self._tick != 0

    def set_speed(self, speed):
        """Playback speed factor, 1 = one 5-min step per STEP_SECONDS."""
        self._speed = speed

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
        self._position = float(index)
        self._update(emit=True)

    def step(self, frames):
        """Select the frame `frames` later (earlier if negative), stopping
        at the ends, and pause playback."""
        if not self._entries:
            return
        self.set_playing(False)
        index = min(max(self.index + frames, 0), len(self._entries) - 1)
        self._adjustment.set_value(index)

    def set_playing(self, playing):
        if playing == self.playing or (playing and len(self._entries) < 2):
            return
        if playing:
            if self.index == len(self._entries) - 1:
                self._adjustment.set_value(0)
            self._last_tick = 0
            renderer = self.get_native().get_renderer() if self.get_native() else None
            self._fps = SOFTWARE_FPS if isinstance(renderer, Gsk.CairoRenderer) else FPS
            log.debug("playing at up to %d updates/s (%s)", self._fps,
                      type(renderer).__name__)
            # Driven by the frame clock, at most self._fps updates per second.
            self._tick = self.add_tick_callback(self._on_tick)
        else:
            self.remove_tick_callback(self._tick)
            self._tick = 0
            # Stop on a whole frame.
            self._adjustment.set_value(round(self._adjustment.get_value()))
        self._set_play_button(playing)

    def _set_play_button(self, playing):
        label = "Pause" if playing else "Play"
        self._play.set_icon_name("media-playback-pause-symbolic" if playing
                                 else "media-playback-start-symbolic")
        self._play.set_tooltip_text(label)
        self._play.update_property([Gtk.AccessibleProperty.LABEL], [label])

    def _on_tick(self, widget, clock):
        now = clock.get_frame_time()
        if self._last_tick and not due(now - self._last_tick, self._fps):
            return GLib.SOURCE_CONTINUE
        seconds = (now - self._last_tick) / 1e6 if self._last_tick else 0.0
        self._last_tick = now
        count = len(self._entries)
        position = advance(self._position, step_frames(seconds, self._speed),
                           count, self._ready)
        if position != self._position:
            previous = self.index
            self._position = position
            with GObject.signal_handler_block(self._adjustment, self._changed):
                self._adjustment.set_value(min(position, count - 1))
            index, fraction = blend(position, count)
            if index != previous:
                self._update(emit=True)
            self.emit("blend", index, fraction)
        return GLib.SOURCE_CONTINUE

    def _on_value_changed(self, adjustment):
        # Snap to whole frames while dragging (and when playback stops).
        value = adjustment.get_value()
        if value != round(value):
            adjustment.set_value(round(value))
            return
        self._position = value
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
