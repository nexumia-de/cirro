"""Sidebar with the list of places (docs/places.md, sidebar): the list
view of the same store as the map pins, the keyboard and screen reader
route to them, and the place to reorder them."""
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

from cirro.pins import OWN_ICON, PLACE_ICON, status  # noqa: E402


class PlacesView(Gtk.ScrolledWindow):
    """`activated(place id)` when a row is chosen."""

    __gsignals__ = {
        "activated": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, store):
        super().__init__(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        self._store = store
        self._selected = None
        self._list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self._list.update_property([Gtk.AccessibleProperty.LABEL], ["Places"])
        self._list.connect("row-activated", self._on_row_activated)
        self.set_child(self._list)
        store.connect("changed", lambda *_: self._rebuild())
        self._rebuild()

    def select(self, place_id):
        self._selected = place_id
        self._update_selection()

    def _rebuild(self):
        self._list.bind_model(self._store.model, self._row)
        self._update_selection()

    def _update_selection(self):
        for row in self._rows():
            if row.place_id == self._selected:
                self._list.select_row(row)
                return
        self._list.unselect_all()

    def _rows(self):
        row = self._list.get_first_child()
        while row:
            yield row
            row = row.get_next_sibling()

    def _row(self, place):
        notes = []
        state = status(place)
        if state and place.title != "My Location":
            notes.append(state)
        if not place.has_position:
            notes.append("Unknown position")
        if place is self._store.default:
            notes.append("Default place")
        row = Adw.ActionRow(title=GLib.markup_escape_text(place.title),
                            subtitle=GLib.markup_escape_text(" · ".join(notes)),
                            activatable=True)
        row.place_id = place.id
        row.add_prefix(Gtk.Image(icon_name=OWN_ICON if place.own else PLACE_ICON,
                                 accessible_role=Gtk.AccessibleRole.PRESENTATION))
        menu = Gio.Menu()
        target = GLib.Variant("s", place.id)
        index = self._store.index(place)
        if not place.own:
            if index > 1:
                item = Gio.MenuItem.new("Move _Up", None)
                item.set_action_and_target_value("win.place-up", target)
                menu.append_item(item)
            if index < self._store.model.get_n_items() - 1:
                item = Gio.MenuItem.new("Move _Down", None)
                item.set_action_and_target_value("win.place-down", target)
                menu.append_item(item)
        for label, action in (("_Rename…", "win.rename-place"),
                              ("Set as _Default", "win.set-default-place")):
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value(action, target)
            menu.append_item(item)
        if not place.own:
            item = Gio.MenuItem.new("_Delete", None)
            item.set_action_and_target_value("win.delete-place", target)
            menu.append_item(item)
        button = Gtk.MenuButton(icon_name="view-more-symbolic",
                                menu_model=menu, valign=Gtk.Align.CENTER,
                                css_classes=["flat"],
                                tooltip_text="Place Actions")
        button.update_property([Gtk.AccessibleProperty.LABEL],
                               [f"Actions for {place.title}"])
        row.add_suffix(button)
        return row

    def _on_row_activated(self, listbox, row):
        self.emit("activated", row.place_id)
