import logging
import os
from pathlib import Path

import gi

gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gio, GLib, GObject, Gtk, Shumate  # noqa: E402

from cirro.frames import FrameStore  # noqa: E402
from cirro.legend import Legend  # noqa: E402
from cirro.location import Location  # noqa: E402
from cirro.nowcast_view import NowcastView  # noqa: E402
from cirro.radar_layer import RadarLayer  # noqa: E402
from cirro import radar_source  # noqa: E402
from cirro.radar_source import RadarSource  # noqa: E402
from cirro.renderer import CAPACITY, FrameRenderer  # noqa: E402
from cirro.timebar import SPEEDS, TimeBar, clock  # noqa: E402

log = logging.getLogger(__name__)

# Initial view: all of Germany on a 360 px wide phone screen.
GERMANY = (51.2, 10.4, 5.8)
# Zoom for "Show My Location": the region around the user.
LOCATION_ZOOM = 8.5
# Below this width the map scale would overlap the attribution.
SCALE_MIN_WIDTH = 600
# Below this height the nowcast chart leaves too little map; the
# sentence stays.
CHART_MIN_HEIGHT = 560


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Cirro")
        self.set_default_size(800, 600)
        self.set_size_request(360, 294)
        self._entries = []
        self._centre_on_fix = False

        menu = Gio.Menu()
        speeds = Gio.Menu()
        for label, factor in SPEEDS:
            speeds.append(label, f"app.playback-speed({factor})")
        menu.append_section("Playback Speed", speeds)
        about = Gio.Menu()
        about.append("_About Cirro", "app.about")
        menu.append_section(None, about)
        self._title = Adw.WindowTitle(title="Cirro")
        header = Adw.HeaderBar(title_widget=self._title)
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu,
            primary=True, tooltip_text="Main Menu"))
        self._refresh = Gtk.Button(icon_name="view-refresh-symbolic",
                                   tooltip_text="Reload Radar")
        self._refresh.connect("clicked", lambda *_: self.source.refresh())
        header.pack_end(self._refresh)
        locate = Gtk.Button(icon_name="find-location-symbolic",
                            tooltip_text="Show My Location")
        locate.connect("clicked", self._on_locate)
        header.pack_start(locate)

        self._banner = Adw.Banner(button_label="Reload")
        self._banner.connect("button-clicked", lambda *_: self.source.refresh())

        self.map = Shumate.SimpleMap()
        registry = Shumate.MapSourceRegistry.new_with_defaults()
        self.map.set_map_source(registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK))
        # DWD source note at the data; the full alteration note is in the
        # About dialog (docs/data-sources.md, licences and attribution).
        self.map.get_license().set_extra_text(
            "Based on data from Deutscher Wetterdienst")
        # Kilometres only (Germany). Narrow windows have no room for the
        # scale next to the attribution, which has to stay readable, so
        # it is hidden there.
        scale = self.map.get_scale()
        scale.set_unit(Shumate.Unit.METRIC)
        narrow = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse(f"max-width: {SCALE_MIN_WIDTH}sp"))
        narrow.add_setter(scale, "visible", False)
        self.add_breakpoint(narrow)
        viewport = self.map.get_viewport()
        viewport.set_min_zoom_level(4)
        viewport.set_max_zoom_level(12)
        lat, lon, zoom = GERMANY
        self.map.get_map().center_on(lat, lon)
        viewport.set_zoom_level(zoom)
        self.radar_layer = RadarLayer(viewport)
        self.map.add_overlay_layer(self.radar_layer)
        self._markers = Shumate.MarkerLayer(viewport=viewport)
        self._me = Shumate.Point(visible=False)
        self._me.update_property([Gtk.AccessibleProperty.LABEL], ["My location"])
        self._markers.add_marker(self._me)
        self.map.add_overlay_layer(self._markers)

        self.timebar = TimeBar(ready=self._is_rendered)
        self.timebar.connect("selected", self._on_selected)
        self.timebar.connect("blend", self._on_blend)
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.append(self.timebar)
        bottom.append(Legend())

        self._toasts = Adw.ToastOverlay(child=self.map)
        view = Adw.ToolbarView(content=self._toasts)
        view.add_top_bar(header)
        view.add_top_bar(self._banner)
        view.add_bottom_bar(Adw.Clamp(maximum_size=560, child=bottom))
        self.set_content(view)

        demo = os.environ.get("CIRRO_DEMO_DATA")
        if demo:
            # Recorded data, e.g. tests/data/demo for screenshots.
            self.source = radar_source.demo(demo)
        else:
            cache = Path(GLib.get_user_cache_dir()) / "cirro" / "frames"
            self.source = RadarSource(FrameStore(cache))
        self.source.connect("changed", self._on_frames_changed)
        self.source.connect("failed", self._on_failed)
        self.source.connect("notify::stale", self._update_banner)
        self.source.bind_property(
            "loading", self._refresh, "sensitive",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN)
        self.renderer = FrameRenderer(self._on_rendered)

        self.location = Location()
        self.location.connect("changed", self._on_location)
        self.location.connect("failed", self._on_location_failed)
        self._location_wanted = False

        # Point nowcast at the own location or the map centre.
        self.nowcast = NowcastView(viewport, self.location)
        bottom.prepend(self.nowcast)
        short = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse(f"max-height: {CHART_MIN_HEIGHT}sp"))
        short.add_setter(self.nowcast.chart, "visible", False)
        self.add_breakpoint(short)

        # Poll and animate only while the window can be seen.
        self.connect("notify::suspended", self._update_active)
        self.connect("map", self._update_active)
        self.connect("unmap", self._update_active)
        self.source.start()

    def _update_active(self, *_):
        active = self.get_mapped() and not self.get_property("suspended")
        self.source.set_active(active)
        if not active:
            self.timebar.set_playing(False)
            self.location.stop()
        elif self._location_wanted:
            self.location.start(self)

    # Radar frames

    def _on_frames_changed(self, source):
        self._entries = source.store.timeline()
        t0 = source.store.analysis_time
        self._title.set_subtitle(f"Updated {clock(t0)}" if t0 else "")
        self.timebar.set_frames(self._entries, t0)
        self.nowcast.set_frames(self._entries, t0)
        self._update_banner()

    def _is_rendered(self, index):
        return self.renderer.get(self._entries[index]) is not None

    def _on_selected(self, timebar, index):
        rendered = self.renderer.get(self._entries[index])
        if rendered:
            self.radar_layer.set_frame(rendered.texture, rendered.bounds)
        # Render the selected frame first, then the ones playback needs next.
        n = len(self._entries)
        ahead = [(index + k) % n for k in range(CAPACITY - 1)]
        behind = [(index - 1) % n]
        self.renderer.request([self._entries[i] for i in ahead + behind])

    def _on_blend(self, timebar, index, fraction):
        # Playback between two frames: crossfade their textures.
        rendered = self.renderer.get(self._entries[index])
        if not rendered:
            return
        following = None
        if fraction and index + 1 < len(self._entries):
            following = self.renderer.get(self._entries[index + 1])
        if following and following.bounds != rendered.bounds:
            following = None
        self.radar_layer.set_frame(rendered.texture, rendered.bounds,
                                   following and following.texture, fraction)

    def _on_rendered(self, name):
        if self._entries and self._entries[self.timebar.index].name == name:
            rendered = self.renderer.get(self._entries[self.timebar.index])
            self.radar_layer.set_frame(rendered.texture, rendered.bounds)
        return GLib.SOURCE_REMOVE

    def _update_banner(self, *_):
        t0 = self.source.store.analysis_time
        # Without any data the failure toast explains the empty map.
        self._banner.set_revealed(self.source.stale and t0 is not None)
        if t0:
            self._banner.set_title(f"Radar data from {clock(t0)} is out of date")

    def _on_failed(self, source, message, show):
        if not show:
            return
        toast = Adw.Toast(title="Radar data could not be loaded",
                          button_label="Retry", timeout=0)
        toast.connect("button-clicked", lambda *_: self.source.refresh())
        self._toasts.add_toast(toast)

    # Own location

    def _on_locate(self, button):
        self._location_wanted = True
        if self.location.fix:
            self._go_to(*self.location.fix[:2])
        else:
            self._centre_on_fix = True
        self.location.start(self)

    def _go_to(self, latitude, longitude):
        zoom = max(self.map.get_viewport().get_zoom_level(), LOCATION_ZOOM)
        self.map.get_map().go_to_full(latitude, longitude, zoom)

    def _on_location(self, location, latitude, longitude, accuracy):
        self._me.set_location(latitude, longitude)
        self._me.set_visible(True)
        if self._centre_on_fix:
            self._centre_on_fix = False
            self._go_to(latitude, longitude)

    def _on_location_failed(self, location, message):
        self._location_wanted = False
        if self._centre_on_fix:
            self._centre_on_fix = False
            self._toasts.add_toast(Adw.Toast(title="Location unavailable"))
