"""Long press (touch) or right click (mouse) on the map: a menu at that
spot to save it as a place or to show the rain there without saving
(issue #51, docs/places.md)."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk  # noqa: E402


class MapPress(GObject.Object):
    """`add(latitude, longitude)` or `show(latitude, longitude)` when the
    user picks a menu item. `enabled()` says whether the map takes the
    gesture now (not while a place is chosen by panning)."""

    __gsignals__ = {
        "add": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        "show": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
    }

    def __init__(self, map_widget, viewport, enabled=lambda: True):
        super().__init__()
        self._map = map_widget
        self._viewport = viewport
        self._enabled = enabled
        self._point = None
        long_press = Gtk.GestureLongPress(touch_only=True)
        long_press.connect("pressed", lambda _, x, y: self._open(x, y))
        right = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        right.connect("pressed", lambda _, n, x, y: self._open(x, y))
        for gesture in (long_press, right):
            gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            map_widget.add_controller(gesture)

        actions = Gio.SimpleActionGroup()
        for name in ("add", "show"):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, n=name: self._chosen(n))
            actions.add_action(action)
        map_widget.insert_action_group("press", actions)
        menu = Gio.Menu()
        menu.append("_Add Place Here", "press.add")
        menu.append("_Show Rain Here", "press.show")
        self._popover = Gtk.PopoverMenu(menu_model=menu, has_arrow=True)
        self._popover.set_parent(map_widget)

    def _open(self, x, y):
        if not self._enabled():
            return
        latitude, longitude = self._viewport.widget_coords_to_location(self._map, x, y)
        self._point = (latitude, longitude)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self._popover.set_pointing_to(rect)
        self._popover.popup()

    def _chosen(self, name):
        if self._point:
            self.emit(name, *self._point)
        return GLib.SOURCE_REMOVE
