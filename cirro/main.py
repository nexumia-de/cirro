import logging
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Shumate  # noqa: E402
from phosh_toolkit import feedback, http  # noqa: E402

from cirro import (  # noqa: E402
    APP_ID,
    NAME,
    NIGHTLY,
    REPO,
    REPO_URL,
    SUPPORT_URL,
    USER_AGENT,
    VERSION_LABEL,
    metainfo,
)
from cirro.data_saver import DataSaver, load_enabled, save_enabled  # noqa: E402
from cirro.notify import background  # noqa: E402
from cirro.notify.watcher import Watcher  # noqa: E402
from cirro.preferences import PreferencesDialog  # noqa: E402
from cirro.settings_file import load_bool, save_bool  # noqa: E402
from cirro.timebar import load_speed, save_speed  # noqa: E402
from cirro.warnings.source import WarningSource  # noqa: E402
from cirro.window import Window  # noqa: E402


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        # --background: started at login for notifications, no window
        # until the user opens the app (issue #25).
        self.add_main_option(
            "background",
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            "Start without a window, for notifications",
            None,
        )
        self._background_start = False
        self._held = False
        self.warnings = None
        self.data_saver = None
        self.watcher = None
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
            "playback-speed", GLib.VariantType("d"), GLib.Variant("d", load_speed())
        )
        speed.connect("change-state", self._on_playback_speed)
        self.add_action(speed)
        # app.save-mobile-data(b): poll less often on metered connections.
        saver = Gio.SimpleAction.new_stateful(
            "save-mobile-data", None, GLib.Variant("b", load_enabled())
        )
        saver.connect("change-state", self._on_save_mobile_data)
        self.add_action(saver)
        # app.notifications(b): warnings and rain at the default place,
        # also with the window closed.
        notify = Gio.SimpleAction.new_stateful(
            "notifications", None, GLib.Variant("b", load_bool("notifications", "enabled", False))
        )
        notify.connect("change-state", self._on_notifications)
        self.add_action(notify)
        preferences = Gio.SimpleAction.new("preferences", None)
        preferences.connect("activate", self._on_preferences)
        self.add_action(preferences)
        # app.show-places: the list of places; on the phone its own page.
        places = Gio.SimpleAction.new("show-places", None)
        places.connect("activate", self._on_show_places)
        self.add_action(places)
        # app.layers: the layer picker; app.show-layer("id:variant"): show
        # a map layer (base or overlay, "radar" for the radar), for
        # screenshots and testing (docs/map-layers.md).
        layers = Gio.SimpleAction.new("layers", None)
        layers.connect(
            "activate", lambda *_: self._window_call(lambda w: w.layers.present_picker())
        )
        self.add_action(layers)
        show_layer = Gio.SimpleAction.new("show-layer", GLib.VariantType("s"))
        show_layer.connect(
            "activate",
            lambda _, value: self._window_call(lambda w: w.layers.show_layer(value.unpack())),
        )
        self.add_action(show_layer)
        # app.report-problem: issue through the user's token or GitHub's form
        # (phosh-toolkit docs/feedback.md); the token is kept in the keyring.
        feedback.install(
            self,
            repo=REPO,
            app_name=NAME,
            version=VERSION_LABEL,
            client=http.Client(USER_AGENT),
        )
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
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        # Running from the source tree: the app icon is not installed.
        icons = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icons.is_dir():
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(icons))

    def do_handle_local_options(self, options):
        self._background_start = options.contains("background")
        return -1

    def _shared(self):
        """Warnings and the data saver, shared by the window and the
        notifications."""
        if self.warnings is None:
            self.data_saver = DataSaver(load_enabled())
            self.warnings = WarningSource(live=not os.environ.get("CIRRO_DEMO_DATA"))
            self.watcher = Watcher(self, self.warnings, self.data_saver)
            if self.lookup_action("notifications").get_state().unpack():
                self._set_watching(True)

    def _set_watching(self, on):
        if on:
            self.watcher.start()
            if not self._held:
                self.hold()  # keep running after the window closes
                self._held = True
        else:
            self.watcher.stop()
            if self._held:
                self.release()
                self._held = False

    def _on_notifications(self, action, value):
        on = value.unpack()
        if not on:
            action.set_state(value)
            save_bool("notifications", "enabled", False)
            self._set_watching(False)
            background.request(self.props.active_window, False, lambda _: None)
            return

        def answered(allowed):
            action.set_state(GLib.Variant("b", allowed))
            save_bool("notifications", "enabled", allowed)
            self._set_watching(allowed)
            if not allowed and self.props.active_window:
                self.props.active_window.show_toast(
                    "Notifications need permission to run in the background"
                )

        background.request(self.props.active_window, True, answered)

    def do_activate(self):
        self._shared()
        if self._background_start:
            # Login start: wait in the background (the watcher holds the
            # app) until a notification or the launcher opens the window.
            self._background_start = False
            if self._held:
                return
        window = self.props.active_window
        if window is None:
            window = Window(self)
            window.timebar.set_speed(self.lookup_action("playback-speed").get_state().unpack())
            if NIGHTLY:
                # libadwaita's striped header bar for development builds.
                window.add_css_class("devel")
        window.present()

    def _window_call(self, function):
        if self.props.active_window:
            function(self.props.active_window)

    def _on_step_time(self, action, frames):
        if self.props.active_window:
            self.props.active_window.timebar.step(frames.unpack())

    def _on_preferences(self, *_):
        window = self.props.active_window
        if window:
            PreferencesDialog(
                window.places,
                self.lookup_action("playback-speed"),
                self.lookup_action("save-mobile-data"),
                self.lookup_action("notifications"),
            ).present(window)

    def _on_show_places(self, *_):
        if self.props.active_window:
            self.props.active_window.split.set_show_content(False)

    def _on_save_mobile_data(self, action, value):
        action.set_state(value)
        save_enabled(value.unpack())
        for window in self.get_windows():
            if hasattr(window, "data_saver"):
                window.data_saver.set_enabled(value.unpack())

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
            issue_url=feedback.issue_url(REPO, VERSION_LABEL),
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
            "Based on data from Deutscher Wetterdienst, gridded data reproduced graphically",
            Gtk.License.CUSTOM,
            "Radar composites reprojected and coloured by Weather Radar "
            "(Cirro). Licensed "
            "under <a href='https://creativecommons.org/licenses/by/4.0/'>"
            "CC BY 4.0</a>.",
        )
        dialog.add_legal_section(
            "Radar for Denmark",
            "Based on data from DMI (Danmarks Meteorologiske Institut)",
            Gtk.License.CUSTOM,
            "Reflectivity composites converted to rain rates, reprojected "
            "and coloured by Weather Radar (Cirro). Licensed under "
            "<a href='https://creativecommons.org/licenses/by/4.0/'>"
            "CC BY 4.0</a>.",
        )
        dialog.add_legal_section(
            "Map Layers",
            "Based on data from Deutscher Wetterdienst",
            Gtk.License.CUSTOM,
            "Weather maps from the Deutscher Wetterdienst's map service, "
            "shown unchanged, under "
            "<a href='https://creativecommons.org/licenses/by/4.0/'>"
            "CC BY 4.0</a>. Warning, pollen and health weather areas: "
            "© GeoBasis-DE / BKG. Satellite images and lightning from "
            "satellite: © EUMETSAT.",
        )
        dialog.add_legal_section(
            "Map Data",
            "© OpenStreetMap contributors",
            Gtk.License.CUSTOM,
            "Available under the <a href='https://www.openstreetmap.org/"
            "copyright'>Open Database License</a>. Place names and search "
            "by Nominatim.",
        )
        # Bundled libraries (docs/dependencies.md); full licence texts are
        # in /app/share/licenses/de.nexumia.Cirro/.
        for name, holder, license_type, text in (
            ("libshumate", "© The libshumate authors", Gtk.License.LGPL_2_1, None),
            (
                "protobuf-c",
                "© Dave Benson and the protobuf-c authors",
                Gtk.License.CUSTOM,
                "BSD-2-Clause",
            ),
            (
                "NumPy",
                "© NumPy Developers",
                Gtk.License.CUSTOM,
                "BSD-3-Clause; includes code under 0BSD, MIT, Zlib and CC0-1.0.",
            ),
            ("h5py", "© Andrew Collette and contributors", Gtk.License.CUSTOM, "BSD-3-Clause"),
            ("HDF5", "© The HDF Group", Gtk.License.CUSTOM, "BSD-3-Clause"),
        ):
            dialog.add_legal_section(name, holder, license_type, text)
        dialog.present(self.props.active_window)


def main(argv):
    # CIRRO_DEBUG=1 logs downloads, render timings, memory and CPU time
    # (docs/radar-architecture.md, measuring on the phone).
    logging.basicConfig(format="cirro: %(name)s: %(message)s")
    if os.environ.get("CIRRO_DEBUG"):
        logging.getLogger("cirro").setLevel(logging.DEBUG)
    return Application().run(argv)
