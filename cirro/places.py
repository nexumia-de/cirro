"""Saved places, the own location and the default place
(docs/places.md).

The store keeps them in a `Gio.ListStore`, the list model behind the map
pins and the sidebar, and saves them as JSON in the data directory (in
the Flatpak: ~/.var/app/<app id>/data/cirro/places.json). No GTK, so it
is tested without a display."""
import json
import logging
import math
import os
import uuid
from pathlib import Path

from gi.repository import Gio, GLib, GObject

log = logging.getLogger(__name__)

PATH = Path(GLib.get_user_data_dir()) / "cirro" / "places.json"
VERSION = 1
# Id of the own location, which is always the first place.
OWN = "own"
# A fix this far from the stored own position renames the own location.
RENAME_AFTER_M = 1000


def distance_m(a, b):
    """Rough distance in metres between two (latitude, longitude)."""
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def coordinates(latitude, longitude):
    """Fallback name of a place: "52.52° N, 13.40° E"."""
    ns = "N" if latitude >= 0 else "S"
    ew = "E" if longitude >= 0 else "W"
    return f"{abs(latitude):.2f}° {ns}, {abs(longitude):.2f}° {ew}"


class Place(GObject.Object):
    """A saved place, or the own location (`own`). Its `title` is the
    custom name, else the default name from reverse geocoding, else its
    coordinates."""

    __gtype_name__ = "CirroPlace"

    id = GObject.Property(type=str)
    own = GObject.Property(type=bool, default=False)
    # The own location has no position until the first fix.
    has_position = GObject.Property(type=bool, default=False)
    latitude = GObject.Property(type=float, default=0.0)
    longitude = GObject.Property(type=float, default=0.0)
    custom_name = GObject.Property(type=str, default="")
    default_name = GObject.Property(type=str, default="")
    # Own location: moved by hand since the last fix.
    manual = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for name in ("custom-name", "default-name", "latitude", "longitude",
                     "has-position"):
            self.connect(f"notify::{name}", lambda *_: self.notify("title"))

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def title(self):
        if self.custom_name:
            return self.custom_name
        if self.default_name:
            return self.default_name
        if self.has_position:
            return coordinates(self.latitude, self.longitude)
        return "My Location" if self.own else ""

    @property
    def position(self):
        return (self.latitude, self.longitude) if self.has_position else None

    def to_json(self):
        data = {"id": self.id}
        if self.has_position:
            data["latitude"] = self.latitude
            data["longitude"] = self.longitude
        if self.custom_name:
            data["name"] = self.custom_name
        if self.default_name:
            data["default_name"] = self.default_name
        if self.manual:
            data["manual"] = True
        return data

    @classmethod
    def from_json(cls, data, own=False):
        place = cls(id=OWN if own else str(data["id"]), own=own,
                    custom_name=str(data.get("name", "")),
                    default_name=str(data.get("default_name", "")),
                    manual=bool(data.get("manual", False)))
        if "latitude" in data and "longitude" in data:
            place.set_position(float(data["latitude"]), float(data["longitude"]))
        return place

    def set_position(self, latitude, longitude):
        self.freeze_notify()
        self.latitude = latitude
        self.longitude = longitude
        self.has_position = True
        self.thaw_notify()


class PlaceStore(GObject.Object):
    """`model` lists the own location first, then the saved places in the
    user's order. Every change is saved at once; `changed` follows it.
    `read_only` (recorded demo places) never writes."""

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, path=PATH, read_only=False):
        super().__init__()
        self.path = Path(path)
        self.read_only = read_only
        self.model = Gio.ListStore(item_type=Place)
        self._default = OWN
        # The location portal is started at launch once it gave a fix.
        self.location_enabled = False
        self._load()

    # Reading and writing

    def _load(self):
        data = {}
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict) or data.get("version") != VERSION:
                raise ValueError(f"unknown version {data.get('version')!r}")
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as error:
            # Keep the broken file for inspection; start empty.
            log.warning("%s unreadable, starting without places: %s",
                        self.path, error)
            data = {}
            if not self.read_only:
                try:
                    self.path.replace(self.path.with_suffix(".json.bad"))
                except OSError:
                    pass
        own = Place.from_json(data.get("own") or {}, own=True)
        places = [own]
        for item in data.get("places", []):
            try:
                places.append(Place.from_json(item))
            except (KeyError, TypeError, ValueError) as error:
                log.warning("skipping broken place %r: %s", item, error)
        self.model.splice(0, 0, places)
        for place in places:
            self._watch(place)
        self._default = str(data.get("default", OWN))
        self.location_enabled = bool(data.get("location_enabled", False))

    def _watch(self, place):
        for name in ("latitude", "longitude", "custom-name", "default-name",
                     "manual", "has-position"):
            place.connect(f"notify::{name}", self._on_place_changed)

    def _on_place_changed(self, *_):
        self.save()

    def save(self):
        if not self.read_only:
            data = {
                "version": VERSION,
                "default": self._default,
                "location_enabled": self.location_enabled,
                "own": self.own.to_json(),
                "places": [p.to_json() for p in self.places()],
            }
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(data, indent=1,
                                                ensure_ascii=False))
                os.replace(temporary, self.path)
            except OSError as error:
                log.warning("could not save places: %s", error)
        self.emit("changed")

    # Queries

    @property
    def own(self):
        return self.model.get_item(0)

    def places(self):
        """The saved places, without the own location."""
        return [self.model.get_item(i) for i in range(1, self.model.get_n_items())]

    def get(self, place_id):
        for i in range(self.model.get_n_items()):
            place = self.model.get_item(i)
            if place.id == place_id:
                return place
        return None

    def index(self, place):
        found, position = self.model.find(place)
        return position if found else -1

    @property
    def default(self):
        """The default place; the own location if the chosen one was
        deleted."""
        return self.get(self._default) or self.own

    @default.setter
    def default(self, place):
        self._default = place.id if place else OWN
        self.save()

    # Changes

    def add(self, latitude, longitude, default_name="", custom_name=""):
        place = Place(id=uuid.uuid4().hex, default_name=default_name,
                      custom_name=custom_name)
        place.set_position(latitude, longitude)
        self._watch(place)
        self.model.append(place)
        self.save()
        return place

    def remove(self, place):
        """Remove a saved place; returns its position for `restore()`.
        The own location can't be removed."""
        if place.own:
            raise ValueError("the own location can't be removed")
        position = self.index(place)
        if position < 0:
            return -1
        self.model.remove(position)
        self.save()
        return position

    def restore(self, place, position):
        """Undo `remove()`."""
        position = max(1, min(position, self.model.get_n_items()))
        self.model.insert(position, place)
        self.save()

    def move(self, place, latitude, longitude):
        """New position chosen by the user. The default name is looked up
        again (empty until then); a custom name stays."""
        place.freeze_notify()
        place.set_position(latitude, longitude)
        place.default_name = ""
        if place.own:
            place.manual = True
        place.thaw_notify()

    def reorder(self, place, position):
        """Move a saved place to `position` in the list (1 = first after
        the own location)."""
        if place.own:
            return
        current = self.index(place)
        position = max(1, min(position, self.model.get_n_items() - 1))
        if current < 0 or current == position:
            return
        self.model.remove(current)
        self.model.insert(position, place)
        self.save()

    def update_own(self, latitude, longitude):
        """A fix from the location portal: overwrites the stored and any
        hand-set position. Returns True if it moved so far that its
        default name is stale."""
        own = self.own
        moved = (own.position is None or own.manual or
                 distance_m(own.position, (latitude, longitude)) > RENAME_AFTER_M)
        own.freeze_notify()
        own.set_position(latitude, longitude)
        own.manual = False
        if moved:
            own.default_name = ""
        own.thaw_notify()
        if not self.location_enabled:
            self.location_enabled = True
            self.save()
        return moved

    def unnamed(self):
        """Places with a position but no default name yet."""
        return [self.model.get_item(i) for i in range(self.model.get_n_items())
                if self.model.get_item(i).has_position
                and not self.model.get_item(i).default_name]
