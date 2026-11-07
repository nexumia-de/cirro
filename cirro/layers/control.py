"""Map layers in the window: the "Layers" button on the map, the time
bar while a DWD base layer is shown, the legend below the map and the
value under a tap. The window keeps the radar; this switches between
the radar's timeline and a layer's (docs/map-layers.md)."""
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk  # noqa: E402

from cirro.layers import catalogue  # noqa: E402
from cirro.layers.legend import LayerLegend  # noqa: E402
from cirro.layers.manager import LayerManager  # noqa: E402
from cirro.layers.picker import LayerPicker  # noqa: E402

LAYERS_ICON = "de.nexumia.Cirro-layers-symbolic"


class LayerControl:
    def __init__(self, window, simple_map, radar_layer, pins,
                 timebar, radar_legend, legend_box, toasts, radar_timeline,
                 persist=True):
        """`radar_timeline()` gives (entries, analysis time) of the radar,
        to put back on the time bar when the radar is chosen again."""
        self._window = window
        self._timebar = timebar
        self._radar_legend = radar_legend
        self._toasts = toasts
        self._radar_timeline = radar_timeline
        self._map = simple_map
        self._failed_toast = None
        self.manager = LayerManager(simple_map, radar_layer, pins, persist)
        self.manager.connect("changed", self._on_changed)
        self.manager.connect("legend", self._on_legend)
        self.manager.connect("failed", self._on_failed)
        self.legend = LayerLegend()
        legend_box.append(self.legend)
        for prop in ("default-width", "default-height", "maximized",
                     "fullscreened"):
            window.connect(f"notify::{prop}", self.manager.resized)
        window.connect("map", lambda *_: self.manager.resized())

        # Thumb reach: at the end of the time bar, in the bottom bar.
        button = Gtk.Button(icon_name=LAYERS_ICON, tooltip_text="Map Layers",
                            css_classes=["circular", "flat"],
                            valign=Gtk.Align.CENTER, action_name="win.layers")
        button.update_property([Gtk.AccessibleProperty.LABEL], ["Map Layers"])
        timebar.append(button)

        click = Gtk.GestureClick()
        click.connect("released", self._on_tap)
        simple_map.get_map().add_controller(click)
        self._on_changed(self.manager)

    @property
    def radar(self):
        return self.manager.radar

    def present_picker(self):
        LayerPicker(self.manager).present(self._window)

    def show_layer(self, spec):
        """`id` or `id:variant`: as base layer, or switch an overlay on."""
        layer_id, _, variant = spec.partition(":")
        variant = int(variant) if variant.isdigit() else 0
        layer = catalogue.get(layer_id)
        if layer_id == catalogue.RADAR or (layer and layer.role == catalogue.BASE):
            self.manager.set_base(layer_id, variant)
        elif layer:
            self.manager.set_overlay(layer_id, True, variant)

    # Time bar

    def _on_changed(self, manager):
        self._radar_legend.set_visible(manager.radar)
        if manager.radar:
            self.legend.set_legend(None)
            entries, t0 = self._radar_timeline()
            if entries:
                self._timebar.set_frames(entries, t0)
            return
        steps, now = manager.steps()
        if steps:
            self._timebar.set_frames(steps, now, daily=manager.daily)
        elif manager.base is not None and manager.base.timeless:
            self._timebar.set_timeless(manager.base.layer.note or "No time steps")
            manager.follow(None)

    def selected(self, index, valid_time):
        """The time bar selected an entry."""
        if self.manager.radar:
            self.manager.follow(valid_time)
        else:
            self.manager.show(index)

    def ready(self, index):
        return self.manager.ready(index)

    def _on_legend(self, manager, legend):
        title = manager.base.layer.title if manager.base else ""
        self.legend.set_legend(legend, title)

    # Failures and taps

    def _on_failed(self, manager, title):
        if self._failed_toast is not None:
            return
        toast = Adw.Toast(title=f"Map layer “{title}” could not be loaded",
                          button_label="_Retry", timeout=0, use_markup=False)
        toast.connect("button-clicked", lambda *_: self.manager.retry())
        toast.connect("dismissed", lambda *_: setattr(self, "_failed_toast", None))
        self._failed_toast = toast
        self._toasts.add_toast(toast)

    def _on_tap(self, gesture, n_press, x, y):
        if n_press != 1:
            return
        widget = gesture.get_widget()
        viewport = self._map.get_viewport()
        latitude, longitude = viewport.widget_coords_to_location(widget, x, y)

        def show(text):
            if text:
                self._toasts.add_toast(Adw.Toast(title=text, timeout=4,
                                                 use_markup=False))
        self.manager.value_at(latitude, longitude, show)
