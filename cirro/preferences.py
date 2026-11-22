"""Preferences: the place selected at startup, the playback speed and
saving mobile data (docs/places.md, default place; cirro/data_saver.py)."""

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from cirro.timebar import SPEEDS  # noqa: E402


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, store, speed_action, saver_action=None, notify_action=None):
        super().__init__(search_enabled=False)
        self._store = store
        self._places = [store.own] + store.places()
        names = [p.title for p in self._places]
        names[0] = "My Location" if names[0] == "My Location" else f"My Location ({names[0]})"
        place = Adw.ComboRow(
            title="Default Place",
            subtitle="Shown when Weather Radar starts",
            model=Gtk.StringList.new(names),
        )
        default = store.default
        place.set_selected(self._places.index(default) if default in self._places else 0)
        place.connect("notify::selected", self._on_place)

        self._speed_action = speed_action
        speed = Adw.ComboRow(
            title="Playback Speed", model=Gtk.StringList.new([s[0] for s in SPEEDS])
        )
        current = speed_action.get_state().unpack()
        factors = [s[1] for s in SPEEDS]
        speed.set_selected(factors.index(current) if current in factors else 1)
        speed.connect("notify::selected", self._on_speed)

        saver = Adw.SwitchRow(
            title="Save Mobile Data",
            subtitle="On metered connections, update the radar every 15 minutes",
        )
        if saver_action is not None:
            saver.set_active(saver_action.get_state().unpack())
            saver.connect(
                "notify::active",
                lambda row, _: saver_action.change_state(GLib.Variant("b", row.get_active())),
            )

        notify = Adw.SwitchRow(
            title="Notifications",
            subtitle="Warnings and rain starting soon at the default place, "
            "also when Weather Radar is closed",
        )
        if notify_action is not None:
            notify.set_active(notify_action.get_state().unpack())
            # The portal may refuse: follow the action's state, and stop
            # following when the dialog closes.
            handler = notify_action.connect(
                "notify::state", lambda a, _: notify.set_active(a.get_state().unpack())
            )
            self.connect("closed", lambda *_: notify_action.disconnect(handler))
            notify.connect(
                "notify::active",
                lambda row, _: (
                    row.get_active() != notify_action.get_state().unpack()
                    and notify_action.change_state(GLib.Variant("b", row.get_active()))
                ),
            )

        places = Adw.PreferencesGroup(title="Places")
        places.add(place)
        radar = Adw.PreferencesGroup(title="Radar")
        radar.add(speed)
        radar.add(saver)
        page = Adw.PreferencesPage()
        places.add(notify)
        page.add(places)
        page.add(radar)
        self.add(page)

    def _on_place(self, row, _):
        self._store.default = self._places[row.get_selected()]

    def _on_speed(self, row, _):
        factor = SPEEDS[row.get_selected()][1]
        self._speed_action.change_state(GLib.Variant("d", factor))
