"""Preferences: the place selected at startup and the playback speed
(docs/places.md, default place)."""
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from cirro.timebar import SPEEDS  # noqa: E402


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, store, speed_action):
        super().__init__(search_enabled=False)
        self._store = store
        self._places = [store.own] + store.places()
        names = [p.title for p in self._places]
        names[0] = ("My Location" if names[0] == "My Location"
                    else f"My Location ({names[0]})")
        place = Adw.ComboRow(title="Default Place",
                             subtitle="Shown when Cirro starts",
                             model=Gtk.StringList.new(names))
        default = store.default
        place.set_selected(self._places.index(default)
                           if default in self._places else 0)
        place.connect("notify::selected", self._on_place)

        self._speed_action = speed_action
        speed = Adw.ComboRow(title="Playback Speed",
                             model=Gtk.StringList.new([s[0] for s in SPEEDS]))
        current = speed_action.get_state().unpack()
        factors = [s[1] for s in SPEEDS]
        speed.set_selected(factors.index(current) if current in factors else 1)
        speed.connect("notify::selected", self._on_speed)

        places = Adw.PreferencesGroup(title="Places")
        places.add(place)
        radar = Adw.PreferencesGroup(title="Radar")
        radar.add(speed)
        page = Adw.PreferencesPage()
        page.add(places)
        page.add(radar)
        self.add(page)

    def _on_place(self, row, _):
        self._store.default = self._places[row.get_selected()]

    def _on_speed(self, row, _):
        factor = SPEEDS[row.get_selected()][1]
        self._speed_action.change_state(GLib.Variant("d", factor))
