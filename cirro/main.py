import logging
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Shumate  # noqa: E402

from cirro import (APP_ID, NAME, NIGHTLY, REPO_URL, SUPPORT_URL,  # noqa: E402
                   USER_AGENT, VERSION_LABEL, metainfo)
from cirro.preferences import PreferencesDialog  # noqa: E402
from cirro.timebar import load_speed, save_speed  # noqa: E402
from cirro.window import Window  # noqa: E402


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        about = Gio.SimpleAction.new("about", None)
        about.connect("activate", self._on_about)
        self.add_action(about)
        quit_ = Gio.SimpleAction.new("quit", None)
        quit_.connect("activate", lambda *_: self.quit())
        self.add_action(quit_)
        # app.step-time(n): show the radar n frames (of 5 min) later, or
        # earlier if n < 0. An app action rather than win.: GTK exports
        # only these on D-Bus, where screenshots activate them.
        step = Gio.SimpleAction.new("step-time", GLib.VariantType("i"))
        step.connect("activate", self._on_step_time)
        self.add_action(step)
        # app.playback-speed(f): radar playback speed factor (timebar.SPEEDS),
        # set in the preferences, kept across starts.
        speed = Gio.SimpleAction.new_stateful(
            "playback-speed", GLib.VariantType("d"),
            GLib.Variant("d", load_speed()))
        speed.connect("change-state", self._on_playback_speed)
        self.add_action(speed)
        preferences = Gio.SimpleAction.new("preferences", None)
        preferences.connect("activate", self._on_preferences)
        self.add_action(preferences)
        # app.show-places: the list of places; on the phone its own page.
        places = Gio.SimpleAction.new("show-places", None)
        places.connect("activate", self._on_show_places)
        self.add_action(places)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.preferences", ["<Control>comma"])
        self.set_accels_for_action("app.step-time(1)", ["<Control>Right"])
        self.set_accels_for_action("app.step-time(-1)", ["<Control>Left"])

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Map tile requests (OSM tile policy: identify the application).
        Shumate.set_user_agent(USER_AGENT)
        # Pin sizes (docs/places.md, pins).
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # Running from the source tree: the app icon is not installed.
        icons = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icons.is_dir():
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) \
                .add_search_path(str(icons))

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = Window(self)
            window.timebar.set_speed(
                self.lookup_action("playback-speed").get_state().unpack())
            if NIGHTLY:
                # libadwaita's striped header bar for development builds.
                window.add_css_class("devel")
        window.present()

    def _on_step_time(self, action, frames):
        if self.props.active_window:
            self.props.active_window.timebar.step(frames.unpack())

    def _on_preferences(self, *_):
        window = self.props.active_window
        if window:
            PreferencesDialog(window.places,
                              self.lookup_action("playback-speed")).present(window)

    def _on_show_places(self, *_):
        if self.props.active_window:
            self.props.active_window.split.set_show_content(False)

    def _on_playback_speed(self, action, value):
        action.set_state(value)
        save_speed(value.unpack())
        if self.props.active_window:
            self.props.active_window.timebar.set_speed(value.unpack())

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name=NAME,
            application_icon=APP_ID,
            version=VERSION_LABEL,
            developer_name="suitably",
            website=REPO_URL,
            issue_url=f"{REPO_URL}/issues",
            license_type=Gtk.License.AGPL_3_0,
            comments="Rain radar with a 2-hour forecast. Not affiliated "
                     "with the Deutscher Wetterdienst.",
        )
        # "What's New" from the metainfo, the same text GNOME Software shows.
        notes = metainfo.release_notes(metainfo.find(APP_ID))
        if notes:
            dialog.set_release_notes_version(notes[0])
            dialog.set_release_notes(notes[1])
        dialog.add_link("Support Development", SUPPORT_URL)
        dialog.add_legal_section(
            "Weather Data",
            "Based on data from Deutscher Wetterdienst, "
            "gridded data reproduced graphically",
            Gtk.License.CUSTOM,
            "Radar composites reprojected and coloured by Cirro. Licensed "
            "under <a href='https://creativecommons.org/licenses/by/4.0/'>"
            "CC BY 4.0</a>.")
        dialog.add_legal_section(
            "Map Data", "© OpenStreetMap contributors",
            Gtk.License.CUSTOM,
            "Available under the <a href='https://www.openstreetmap.org/"
            "copyright'>Open Database License</a>. Place names and search "
            "by Nominatim.")
        # Bundled libraries (docs/dependencies.md); full licence texts are
        # in /app/share/licenses/de.nexumia.Cirro/.
        for name, holder, license_type, text in (
                ("libshumate", "© The libshumate authors",
                 Gtk.License.LGPL_2_1, None),
                ("protobuf-c", "© Dave Benson and the protobuf-c authors",
                 Gtk.License.CUSTOM, "BSD-2-Clause"),
                ("NumPy", "© NumPy Developers",
                 Gtk.License.CUSTOM,
                 "BSD-3-Clause; includes code under 0BSD, MIT, Zlib and "
                 "CC0-1.0."),
                ("h5py", "© Andrew Collette and contributors",
                 Gtk.License.CUSTOM, "BSD-3-Clause"),
                ("HDF5", "© The HDF Group",
                 Gtk.License.CUSTOM, "BSD-3-Clause")):
            dialog.add_legal_section(name, holder, license_type, text)
        dialog.present(self.props.active_window)


def main(argv):
    # CIRRO_DEBUG=1 logs downloads, render timings, memory and CPU time
    # (docs/radar-architecture.md, measuring on the phone).
    logging.basicConfig(format="cirro: %(name)s: %(message)s")
    if os.environ.get("CIRRO_DEBUG"):
        logging.getLogger("cirro").setLevel(logging.DEBUG)
    return Application().run(argv)

