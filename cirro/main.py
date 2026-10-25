from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gdk, Gio, Gtk, Shumate  # noqa: E402

from cirro import (APP_ID, NAME, NIGHTLY, REPO_URL, USER_AGENT,  # noqa: E402
                   VERSION_LABEL)
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
        self.set_accels_for_action("app.quit", ["<Control>q"])

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Map tile requests (OSM tile policy: identify the application).
        Shumate.set_user_agent(USER_AGENT)
        # Running from the source tree: the app icon is not installed.
        icons = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icons.is_dir():
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) \
                .add_search_path(str(icons))

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = Window(self)
            if NIGHTLY:
                # libadwaita's striped header bar for development builds.
                window.add_css_class("devel")
        window.present()

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
            "copyright'>Open Database License</a>.")
        # Bundled libraries (docs/dependencies.md); full licence texts are
        # in /app/share/licenses/de.nexumia.Cirro/.
        for name, holder, license_type, text in (
                ("libshumate", "© The libshumate authors",
                 Gtk.License.LGPL_2_1, None),
                ("protobuf-c", "© Dave Benson and the protobuf-c authors",
                 Gtk.License.CUSTOM, "BSD-2-Clause"),
                ("NumPy", "© NumPy Developers",
                 Gtk.License.CUSTOM,
                 "BSD-3-Clause; bundles OpenBLAS (BSD-3-Clause), "
                 "libgfortran (GPL-3.0-or-later with GCC runtime exception) "
                 "and libquadmath (LGPL-2.1-or-later)."),
                ("h5py", "© Andrew Collette and contributors",
                 Gtk.License.CUSTOM,
                 "BSD-3-Clause; bundles HDF5 (BSD-3-Clause) and libaec "
                 "(BSD-2-Clause).")):
            dialog.add_legal_section(name, holder, license_type, text)
        dialog.present(self.props.active_window)


def main(argv):
    return Application().run(argv)

