import logging
import os
from pathlib import Path

import gi

gi.require_version("Shumate", "1.0")
from gi.repository import Adw, Gio, GLib, GObject, Gtk, Shumate  # noqa: E402

from cirro.frames import FrameStore  # noqa: E402
from cirro.legend import Legend  # noqa: E402
from cirro.location import Location  # noqa: E402
from cirro.namer import Namer  # noqa: E402
from cirro.nowcast_view import NowcastView  # noqa: E402
from cirro.pins import PLACE_ICON, PinLayer, status  # noqa: E402
from cirro.places import PlaceStore  # noqa: E402
from cirro.places_view import PlacesView  # noqa: E402
from cirro.radar_layer import RadarLayer  # noqa: E402
from cirro import radar_source  # noqa: E402
from cirro.radar_source import RadarSource  # noqa: E402
from cirro.renderer import CAPACITY, FrameRenderer  # noqa: E402
from cirro.search import SearchDialog  # noqa: E402
from cirro.timebar import TimeBar, clock  # noqa: E402

log = logging.getLogger(__name__)

# Initial view: all of Germany on a 360 px wide phone screen.
GERMANY = (51.2, 10.4, 5.8)
# Zoom for "Show My Location" and a selected place: the region around it.
LOCATION_ZOOM = 8.5
# Below this width the sidebar collapses into its own page.
SIDEBAR_MIN_WIDTH = 600
# Below this width the map scale would overlap the attribution, also
# next to the sidebar.
SCALE_MIN_WIDTH = 860
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
        self._selected = None      # id of the selected place
        self._point = None         # unsaved point: (name, latitude, longitude)
        self._moving = None        # id of the place being moved
        self._live = False         # own location has a fix from this session

        # Places (docs/places.md). Recorded places for screenshots are
        # read only and never looked up.
        demo_places = os.environ.get("CIRRO_DEMO_PLACES")
        if demo_places:
            self.places = PlaceStore(demo_places, read_only=True)
        else:
            self.places = PlaceStore()
        self.namer = Namer(self.places, enabled=not demo_places)
        self.places.connect("changed", self._on_places_changed)
        self._install_actions()

        menu = Gio.Menu()
        menu.append("_Reload Radar", "win.reload")
        menu.append("_Preferences", "app.preferences")
        menu.append("_About Cirro", "app.about")
        self._title = Adw.WindowTitle(title="Cirro")
        header = Adw.HeaderBar(title_widget=self._title)
        header.pack_end(Gtk.MenuButton(
            icon_name="open-menu-symbolic", menu_model=menu,
            primary=True, tooltip_text="Main Menu"))
        locate = Gtk.Button(icon_name="find-location-symbolic",
                            tooltip_text="Show My Location")
        locate.connect("clicked", self._on_locate)
        header.pack_start(locate)
        header.pack_start(Gtk.Button(icon_name="system-search-symbolic",
                                     tooltip_text="Search Places",
                                     action_name="win.search"))
        self._header = header

        # Header while a pin is moved: the map pans under a fixed pin.
        cancel = Gtk.Button(label="_Cancel", use_underline=True)
        cancel.connect("clicked", lambda *_: self._end_move())
        done = Gtk.Button(label="_Done", use_underline=True,
                          css_classes=["suggested-action"])
        done.connect("clicked", lambda *_: self._finish_move())
        self._move_header = Adw.HeaderBar(
            title_widget=Adw.WindowTitle(title="Move Place",
                                         subtitle="Pan the map to the new spot"),
            show_start_title_buttons=False, show_end_title_buttons=False,
            visible=False)
        self._move_header.pack_start(cancel)
        self._move_header.pack_end(done)

        self._banner = Adw.Banner(button_label="Reload")
        self._banner.connect("button-clicked", lambda *_: self.source.refresh())

        self.map = Shumate.SimpleMap()
        registry = Shumate.MapSourceRegistry.new_with_defaults()
        self.map.set_map_source(registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK))
        # DWD source note at the data; the full alteration note is in the
        # About dialog (docs/data-sources.md, licences and attribution).
        self.map.get_license().set_extra_text(
            "Based on data from Deutscher Wetterdienst")
        # Kilometres only (Germany). Narrow maps have no room for the
        # scale next to the attribution, which has to stay readable, so
        # it is hidden there (breakpoints below).
        scale = self.map.get_scale()
        scale.set_unit(Shumate.Unit.METRIC)
        viewport = self.map.get_viewport()
        viewport.set_min_zoom_level(4)
        viewport.set_max_zoom_level(12)
        lat, lon, zoom = GERMANY
        self.map.get_map().center_on(lat, lon)
        viewport.set_zoom_level(zoom)
        self.radar_layer = RadarLayer(viewport)
        self.map.add_overlay_layer(self.radar_layer)
        self.pins = PinLayer(viewport, self.places)
        self.pins.connect("activated", lambda _, place_id: self._select(place_id))
        self.map.add_overlay_layer(self.pins)
        # A tap on an empty spot shows the nowcast there (issue #19).
        tap = Gtk.GestureClick()
        tap.connect("released", self._on_tap)
        self.map.get_map().add_controller(tap)
        # The fixed pin of the move mode, at the centre of the map.
        self._crosshair = Gtk.Image(
            icon_name=PLACE_ICON, css_classes=["osd", "cirro-point"],
            halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
            can_target=False, visible=False)
        overlay = Gtk.Overlay(child=self.map)
        overlay.add_overlay(self._crosshair)

        self.timebar = TimeBar(ready=self._is_rendered)
        self.timebar.connect("selected", self._on_selected)
        self.timebar.connect("blend", self._on_blend)
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.append(self.timebar)
        bottom.append(Legend())

        self._toasts = Adw.ToastOverlay(child=overlay)
        view = Adw.ToolbarView(content=self._toasts)
        view.add_top_bar(header)
        view.add_top_bar(self._move_header)
        view.add_top_bar(self._banner)
        view.add_bottom_bar(Adw.Clamp(maximum_size=560, child=bottom))

        # Sidebar with the list of places (issue #18).
        self.sidebar = PlacesView(self.places)
        self.sidebar.connect("activated",
                             lambda _, place_id: self._select(place_id, centre=True))
        sidebar_header = Adw.HeaderBar()
        sidebar_header.pack_start(Gtk.Button(icon_name="list-add-symbolic",
                                             tooltip_text="Add Place",
                                             action_name="win.add-place-search"))
        sidebar_view = Adw.ToolbarView(content=self.sidebar)
        sidebar_view.add_top_bar(sidebar_header)
        self._content = Adw.NavigationPage(title="Cirro", child=view)
        self.split = Adw.NavigationSplitView(
            sidebar=Adw.NavigationPage(title="Places", child=sidebar_view),
            content=self._content, show_content=True)
        self.set_content(self.split)

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
        # Reload is in the main menu: the header has no room for it on
        # the phone next to the places' buttons.
        self.source.bind_property(
            "loading", self.lookup_action("reload"), "enabled",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN)
        self.renderer = FrameRenderer(self._on_rendered)

        self.location = Location()
        self.location.connect("changed", self._on_location)
        self.location.connect("failed", self._on_location_failed)
        # Once the portal gave a fix, follow the own location from the
        # start (issue #41).
        self._location_wanted = self.places.location_enabled

        # Point nowcast at the selected place, with its actions.
        self._place_menu = Gio.Menu()
        self._place_actions = Gtk.MenuButton(
            icon_name="view-more-symbolic", menu_model=self._place_menu,
            css_classes=["flat"], tooltip_text="Place Actions")
        self.nowcast = NowcastView(self._place_actions)
        bottom.prepend(self.nowcast)

        # Breakpoints: only the last matching one applies.
        def breakpoint(condition, *setters):
            point = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(condition))
            for widget, name, value in setters:
                point.add_setter(widget, name, value)
            self.add_breakpoint(point)
        no_scale = (scale, "visible", False)
        no_chart = (self.nowcast.chart, "visible", False)
        collapsed = (self.split, "collapsed", True)
        breakpoint(f"max-width: {SCALE_MIN_WIDTH}sp", no_scale)
        breakpoint(f"max-height: {CHART_MIN_HEIGHT}sp", no_scale, no_chart)
        breakpoint(f"max-width: {SIDEBAR_MIN_WIDTH}sp", no_scale, collapsed)
        breakpoint(f"max-width: {SIDEBAR_MIN_WIDTH}sp and "
                   f"max-height: {CHART_MIN_HEIGHT}sp",
                   no_scale, no_chart, collapsed)

        # Start with the default place (issue #40); recorded screenshots
        # keep the view of Germany.
        start = self.places.default
        if not start.has_position:
            start = self.places.own
        if start.has_position:
            self._select(start.id, centre=not demo_places, show=False)
        else:
            self._update_place()
        self.namer.request_unnamed()

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

    # Places: selection, pins and the nowcast (docs/places.md)

    def _install_actions(self):
        def add(name, callback, parameter="s"):
            action = Gio.SimpleAction.new(
                name, GLib.VariantType(parameter) if parameter else None)
            action.connect("activate", lambda _, value: callback(
                value.unpack() if value is not None else None))
            self.add_action(action)

        add("select-place", lambda place_id: self._select(place_id, centre=True))
        add("rename-place", self._rename)
        add("delete-place", self._delete)
        add("set-default-place", self._set_default)
        add("move-place", self._start_move)
        add("move-place-to", self._move_to)
        add("place-up", lambda place_id: self._reorder(place_id, -1))
        add("place-down", lambda place_id: self._reorder(place_id, 1))
        add("add-place", self._add_point, None)
        add("search", self._search, None)
        add("add-place-search", self._add_from_search, None)
        add("reload", lambda _: self.source.refresh(), None)
        app = self.get_application()
        app.set_accels_for_action("win.search", ["<Control>f"])
        app.set_accels_for_action("win.reload", ["<Control>r", "F5"])

    def _place(self, place_id):
        return self.places.get(place_id) if place_id else None

    def _select(self, place_id, centre=False, show=True):
        place = self._place(place_id)
        if place is None:
            return
        self._point = None
        self.pins.show_point(None)
        self._selected = place.id
        self.pins.select(place.id)
        self.sidebar.select(place.id)
        if centre and place.has_position:
            self._go_to(place.latitude, place.longitude)
        if place.own and not place.has_position:
            self._on_locate()
        if show:
            self.split.set_show_content(True)
        self._update_place()

    def _show_point(self, name, latitude, longitude, centre=False):
        """An unsaved point: a tap on the map or a search result."""
        self._point = (name, latitude, longitude)
        self._selected = None
        self.pins.select(None)
        self.sidebar.select(None)
        self.pins.show_point((latitude, longitude))
        if centre:
            self._go_to(latitude, longitude)
        self.split.set_show_content(True)
        self._update_place()

    def _on_tap(self, gesture, presses, x, y):
        if presses != 1 or self._moving:
            return
        latitude, longitude = self.map.get_viewport().widget_coords_to_location(
            self.map.get_map(), x, y)
        self._show_point("", latitude, longitude)

    def _on_places_changed(self, store):
        if self._selected and not self.places.get(self._selected):
            # The selected place was deleted.
            self._selected = None
            start = self.places.default
            if start.has_position:
                self._select(start.id, show=False)
                return
        self._update_place()

    def _update_place(self):
        """Header title, nowcast place and the place's actions."""
        menu = self._place_menu
        menu.remove_all()
        place = self._place(self._selected)
        if self._point:
            name, latitude, longitude = self._point
            title, label, position = name or "Selected Point", "Not saved", \
                (latitude, longitude)
            menu.append("_Add Place", "win.add-place")
        elif place:
            title, position = place.title, place.position
            label = status(place) or ""
            if place.own and not place.manual and not self._live:
                label = "My location, last known"
            target = GLib.Variant("s", place.id)
            items = [("_Rename…", "win.rename-place"),
                     ("_Move on Map", "win.move-place"),
                     ("Move _To…", "win.move-place-to")]
            if place is not self.places.default:
                items.append(("Set as _Default", "win.set-default-place"))
            if not place.own:
                items.append(("_Delete", "win.delete-place"))
            for text, action in items:
                item = Gio.MenuItem.new(text, None)
                item.set_action_and_target_value(action, target)
                menu.append_item(item)
        else:
            title, label, position = "Cirro", "", None
        self._place_actions.set_visible(menu.get_n_items() > 0)
        self._title.set_title(title)
        self._content.set_title(title)
        self.nowcast.set_place(position, label)

    # Place actions

    def _add_point(self, _):
        if not self._point:
            return
        name, latitude, longitude = self._point
        place = self.places.add(latitude, longitude, default_name=name)
        if not name:
            self.namer.request(place)
        self._select(place.id)

    def _search(self, _=None, title="Search Places", chosen=None):
        dialog = SearchDialog(title)
        dialog.connect("chosen", chosen or (
            lambda _, name, lat, lon: self._show_point(name, lat, lon, centre=True)))
        dialog.present(self)

    def _add_from_search(self, _):
        def chosen(dialog, name, latitude, longitude):
            place = self.places.add(latitude, longitude, default_name=name)
            self._select(place.id, centre=True)
        self._search(title="Add Place", chosen=chosen)

    def _move_to(self, place_id):
        place = self._place(place_id)
        if place is None:
            return

        def chosen(dialog, name, latitude, longitude):
            self.places.move(place, latitude, longitude)
            # The search result names the spot; no lookup needed.
            place.default_name = name
            self._select(place.id, centre=True)
        self._search(title="Move To", chosen=chosen)

    def _start_move(self, place_id):
        place = self._place(place_id)
        if place is None or not place.has_position:
            return
        self._select(place.id)
        self._moving = place.id
        self.pins.hide(place.id)
        self.map.get_map().center_on(place.latitude, place.longitude)
        self._crosshair.set_visible(True)
        self._header.set_visible(False)
        self._move_header.set_visible(True)

    def _finish_move(self):
        place = self._place(self._moving)
        if place:
            viewport = self.map.get_viewport()
            self.places.move(place, viewport.get_latitude(),
                             viewport.get_longitude())
            self.namer.request(place)
        self._end_move()

    def _end_move(self):
        self._moving = None
        self.pins.hide(None)
        self._crosshair.set_visible(False)
        self._move_header.set_visible(False)
        self._header.set_visible(True)
        self._update_place()

    def _rename(self, place_id):
        place = self._place(place_id)
        if place is None:
            return
        entry = Adw.EntryRow(title="Name", text=place.custom_name or place.title,
                             activates_default=True)
        names = Gtk.ListBox(css_classes=["boxed-list"],
                            selection_mode=Gtk.SelectionMode.NONE)
        names.append(entry)
        dialog = Adw.AlertDialog(heading="Rename Place", extra_child=names,
                                 default_response="rename",
                                 close_response="cancel")
        dialog.add_response("cancel", "_Cancel")
        if place.custom_name:
            dialog.add_response("reset", "_Use Default Name")
        dialog.add_response("rename", "_Rename")
        dialog.set_response_appearance("rename",
                                       Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda _, response:
                       self._renamed(place, response, entry))
        dialog.present(self)
        entry.grab_focus()

    def _renamed(self, place, response, entry):
        if response == "rename":
            name = " ".join(entry.get_text().split())
            # The default name itself is no custom name.
            place.custom_name = "" if name == place.default_name else name
        elif response == "reset":
            place.custom_name = ""

    def _delete(self, place_id):
        place = self._place(place_id)
        if place is None or place.own:
            return
        title = place.title
        position = self.places.remove(place)
        toast = Adw.Toast(title=f"“{title}” deleted", button_label="_Undo",
                          use_markup=False)
        toast.connect("button-clicked",
                      lambda *_: self.places.restore(place, position))
        self._toasts.add_toast(toast)

    def _set_default(self, place_id):
        place = self._place(place_id)
        if place:
            self.places.default = place

    def _reorder(self, place_id, step):
        place = self._place(place_id)
        if place:
            self.places.reorder(place, self.places.index(place) + step)

    # Own location

    def _on_locate(self, *_):
        self._location_wanted = True
        own = self.places.own
        if own.has_position:
            # Last known position until the fix arrives.
            self._select(own.id, centre=True)
        if not self._live:
            self._centre_on_fix = True
        self.location.start(self)

    def _go_to(self, latitude, longitude):
        zoom = max(self.map.get_viewport().get_zoom_level(), LOCATION_ZOOM)
        self.map.get_map().go_to_full(latitude, longitude, zoom)

    def _on_location(self, location, latitude, longitude, accuracy):
        own = self.places.own
        if self.places.update_own(latitude, longitude):
            self.namer.request(own)
        if not self._live:
            self._live = True
            self.pins.set_live(True)
        if self._selected is None and self._point is None:
            self._select(own.id, show=False)
        if self._centre_on_fix:
            self._centre_on_fix = False
            self._select(own.id, centre=True)
        self._update_place()

    def _on_location_failed(self, location, message):
        # The own pin keeps its last known position.
        self._location_wanted = False
        if self._centre_on_fix:
            self._centre_on_fix = False
            self._toasts.add_toast(Adw.Toast(title="Location unavailable"))
