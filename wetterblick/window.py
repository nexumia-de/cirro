from gi.repository import Adw, Gio, Gtk

from wetterblick import APP_ID


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wetterblick")
        self.set_default_size(800, 600)
        self.set_size_request(360, 294)

        menu = Gio.Menu()
        menu.append("_About Wetterblick", "app.about")
        header = Adw.HeaderBar()
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu,
            primary=True, tooltip_text="Main Menu"))

        # Placeholder until the radar map lands in M1.
        status = Adw.StatusPage(
            icon_name=APP_ID,
            title="Rain Radar",
            description="The radar map is not built yet.",
        )
        view = Adw.ToolbarView(content=status)
        view.add_top_bar(header)
        self.set_content(view)
