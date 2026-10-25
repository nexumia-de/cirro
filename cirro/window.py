import threading

import gi

gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gio, GLib, Gtk, Shumate  # noqa: E402

from cirro import colors, projection, radar, source  # noqa: E402
from cirro.legend import Legend  # noqa: E402
from cirro.radar_layer import RadarLayer, rgba_texture  # noqa: E402

# Initial view: all of Germany on a 360 px wide phone screen.
GERMANY = (51.2, 10.4, 5.8)


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Cirro")
        self.set_default_size(800, 600)
        self.set_size_request(360, 294)
        self._reprojections = {}
        self._loading = False

        menu = Gio.Menu()
        menu.append("_About Cirro", "app.about")
        self._title = Adw.WindowTitle(title="Cirro")
        header = Adw.HeaderBar(title_widget=self._title)
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu,
            primary=True, tooltip_text="Main Menu"))
        self._refresh = Gtk.Button(icon_name="view-refresh-symbolic",
                                   tooltip_text="Reload Radar")
        self._refresh.connect("clicked", lambda *_: self.load_radar())
        header.pack_start(self._refresh)

        self.map = Shumate.SimpleMap()
        registry = Shumate.MapSourceRegistry.new_with_defaults()
        self.map.set_map_source(registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK))
        self.map.get_license().set_extra_text("Radar data: Deutscher Wetterdienst")
        viewport = self.map.get_viewport()
        viewport.set_min_zoom_level(4)
        viewport.set_max_zoom_level(12)
        lat, lon, zoom = GERMANY
        self.map.get_map().center_on(lat, lon)
        viewport.set_zoom_level(zoom)
        self.radar_layer = RadarLayer(viewport)
        self.map.add_overlay_layer(self.radar_layer)

        self._toasts = Adw.ToastOverlay(child=self.map)
        view = Adw.ToolbarView(content=self._toasts)
        view.add_top_bar(header)
        view.add_bottom_bar(Adw.Clamp(maximum_size=560, child=Legend()))
        self.set_content(view)

        self.load_radar()

    def load_radar(self):
        """Fetch, decode and colour the current analysis frame off the main
        thread, then hand the texture to the radar layer."""
        if self._loading:
            return
        self._loading = True
        self._refresh.set_sensitive(False)
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            _, data = source.fetch_analysis()
            frame = radar.decode(data)
            reprojection = self._reprojections.get(frame.grid)
            if reprojection is None:
                reprojection = projection.reproject_grid(frame.grid)
                self._reprojections[frame.grid] = reprojection
            image = colors.colorize(frame, reprojection)
        except Exception as error:  # network, HTTP or format errors
            GLib.idle_add(self._on_failed, error)
            return
        GLib.idle_add(self._on_loaded, frame, reprojection, image)

    def _on_loaded(self, frame, reprojection, image):
        self._loading = False
        self._refresh.set_sensitive(True)
        r = reprojection
        self.radar_layer.set_frame(rgba_texture(image),
                                   (r.north, r.west, r.south, r.east))
        local = GLib.DateTime.new_from_unix_utc(
            int(frame.valid_time.timestamp())).to_local()
        self._title.set_subtitle(f"Radar {local.format('%H:%M')}")

    def _on_failed(self, error):
        self._loading = False
        self._refresh.set_sensitive(True)
        print(f"cirro: radar download failed: {error}")
        toast = Adw.Toast(title="Radar data could not be loaded",
                          button_label="Retry", timeout=0)
        toast.connect("button-clicked", lambda *_: self.load_radar())
        self._toasts.add_toast(toast)
