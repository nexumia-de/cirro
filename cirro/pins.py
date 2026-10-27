"""Places as pins on the map (docs/places.md, pins): one button per
place, a different icon for the own location, the selected pin
highlighted, and an unsaved point for a search result."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Shumate", "1.0")
from gi.repository import GObject, Gtk, Shumate  # noqa: E402

OWN_ICON = "find-location-symbolic"
PLACE_ICON = "mark-location-symbolic"


def status(place):
    """"My location" for the own location, else None."""
    return "My location" if place.own else None


class PinLayer(Shumate.MarkerLayer):
    """`activated(place id)` when a pin is tapped or activated with the
    keyboard."""

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, viewport, store):
        super().__init__(viewport=viewport)
        self._store = store
        self._selected = None
        self._live = False
        # The unsaved point is always the selected one, so it looks like
        # a selected pin; the nowcast row says "Not saved".
        self._point = Shumate.Marker(visible=False, can_target=False)
        self._point.set_child(Gtk.Button(
            icon_name=PLACE_ICON, can_focus=False,
            css_classes=["circular", "suggested-action", "cirro-pin"]))
        self._point.get_child().update_property(
            [Gtk.AccessibleProperty.LABEL], ["Selected point, not saved"])
        store.connect("changed", lambda *_: self._rebuild())
        self._rebuild()

    def select(self, place_id):
        self._selected = place_id
        self._rebuild()

    def set_live(self, live):
        """Whether the own location has a fix from this session; until
        then its pin shows the last known position."""
        self._live = live
        self._rebuild()

    def show_point(self, position):
        """An unsaved point, or none."""
        if position:
            self._point.set_location(*position)
        self._point.set_visible(position is not None)

    def _rebuild(self):
        self.remove_all()
        self.add_marker(self._point)
        for i in range(self._store.model.get_n_items()):
            place = self._store.model.get_item(i)
            if place.has_position:
                self.add_marker(self._marker(place))

    def _marker(self, place):
        selected = place.id == self._selected
        classes = ["circular", "osd", "cirro-pin"]
        if selected:
            classes.append("suggested-action")
        name = place.title
        if place.own:
            state = status(place)
            if not self._live:
                state = "My location, last known"
            label = f"{name}, {state}" if name != "My Location" else state
        else:
            label = name
        if selected:
            label = f"{label}, selected"
        button = Gtk.Button(icon_name=OWN_ICON if place.own else PLACE_ICON,
                            css_classes=classes, tooltip_text=label)
        button.update_property([Gtk.AccessibleProperty.LABEL], [label])
        place_id = place.id
        button.connect("clicked", lambda *_: self.emit("activated", place_id))
        marker = Shumate.Marker(child=button)
        marker.set_location(place.latitude, place.longitude)
        return marker
