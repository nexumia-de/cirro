"""Place search dialog (Nominatim). Searches only when the user presses
Enter: the usage policy forbids search-as-you-type (docs/places.md,
search). A bottom sheet on the phone, a floating dialog on the
desktop."""
import threading

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, GObject, Gtk  # noqa: E402

from cirro import geocode  # noqa: E402


class SearchDialog(Adw.Dialog):
    """`chosen(name, latitude, longitude)` when the user picks a
    result."""

    __gsignals__ = {
        "chosen": (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
    }

    def __init__(self, title="Search Places"):
        super().__init__(title=title, content_width=420, content_height=560)
        self._generation = 0

        self._entry = Gtk.SearchEntry(
            hexpand=True, placeholder_text="City or town",
            activates_default=False)
        self._entry.update_property([Gtk.AccessibleProperty.LABEL],
                                    ["Search places"])
        self._entry.connect("activate", self._on_activate)
        self._entry.connect("stop-search", lambda *_: self.close())
        clamp = Adw.Clamp(child=self._entry, maximum_size=560,
                          margin_start=12, margin_end=12, margin_bottom=6)

        self._results = Gtk.ListBox(css_classes=["boxed-list"],
                                    selection_mode=Gtk.SelectionMode.NONE,
                                    valign=Gtk.Align.START)
        self._results.connect("row-activated", self._on_row_activated)
        results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          margin_start=12, margin_end=12, margin_top=6,
                          margin_bottom=12)
        results.append(self._results)
        results.append(Gtk.Label(label=geocode.ATTRIBUTION, wrap=True,
                                 css_classes=["caption", "dim-label"]))

        self._status = Adw.StatusPage(
            icon_name="system-search-symbolic", title="Search Places",
            description="Enter a city or town and press Enter",
            css_classes=["compact"])
        self._spinner = Gtk.Spinner(spinning=True, width_request=32,
                                    height_request=32,
                                    halign=Gtk.Align.CENTER,
                                    valign=Gtk.Align.CENTER)
        self._stack = Gtk.Stack(vexpand=True)
        self._stack.add_named(self._status, "status")
        self._stack.add_named(self._spinner, "loading")
        self._stack.add_named(Gtk.ScrolledWindow(
            child=Adw.Clamp(child=results, maximum_size=560),
            hscrollbar_policy=Gtk.PolicyType.NEVER), "results")

        header = Adw.HeaderBar()
        view = Adw.ToolbarView(content=self._stack)
        view.add_top_bar(header)
        top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top.append(clamp)
        view.add_top_bar(top)
        self.set_child(view)
        self.set_focus(self._entry)

    def _on_activate(self, entry):
        query = entry.get_text()
        if not query.strip():
            return
        self._generation += 1
        generation = self._generation
        self._stack.set_visible_child_name("loading")

        def work():
            try:
                found = geocode.search(query)
                error = None
            except (OSError, ValueError) as failure:
                found, error = [], failure
            GLib.idle_add(self._show, generation, found, error)

        threading.Thread(target=work, name="search", daemon=True).start()

    def _show(self, generation, found, error):
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        self._results.remove_all()
        if error:
            self._status.set_icon_name("network-offline-symbolic")
            self._status.set_title("Search Unavailable")
            self._status.set_description(
                "Check the internet connection and try again")
            self._stack.set_visible_child_name("status")
        elif not found:
            self._status.set_icon_name("system-search-symbolic")
            self._status.set_title("No Results Found")
            self._status.set_description("Try a different search")
            self._stack.set_visible_child_name("status")
        else:
            for result in found:
                row = Adw.ActionRow(title=GLib.markup_escape_text(result.name),
                                    subtitle=GLib.markup_escape_text(result.detail),
                                    activatable=True)
                row.result = result
                self._results.append(row)
            self._stack.set_visible_child_name("results")
        return GLib.SOURCE_REMOVE

    def _on_row_activated(self, listbox, row):
        result = row.result
        self.emit("chosen", result.name, result.latitude, result.longitude)
        self.close()
