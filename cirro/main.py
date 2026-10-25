from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gdk, Gio, Gtk, Shumate  # noqa: E402

from cirro import APP_ID, REPO_URL, USER_AGENT, VERSION  # noqa: E402
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
        (self.props.active_window or Window(self)).present()

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name="Cirro",
            application_icon=APP_ID,
            version=VERSION,
            developer_name="suitably",
            website=REPO_URL,
            issue_url=f"{REPO_URL}/issues",
            license_type=Gtk.License.AGPL_3_0,
            comments="Rain radar with a 2-hour forecast. Not affiliated "
                     "with the Deutscher Wetterdienst.",
        )
        dialog.add_legal_section(
            "Weather data", "Deutscher Wetterdienst (DWD), open data",
            Gtk.License.CUSTOM, None)
        dialog.add_legal_section(
            "Map data", "© OpenStreetMap contributors",
            Gtk.License.CUSTOM, None)
        dialog.present(self.props.active_window)


def main(argv):
    return Application().run(argv)

