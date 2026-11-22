"""Parse DWD's CAP status zip and find the warnings at a point.

One XML file per warning (CAP 1.2, DWD profile 2.1). Land warnings
carry their area as polygons ("polygonal event area") with holes as
`EXCLUDE_POLYGON` geocodes; the warn cell areas only name the
municipalities (docs/data-sources.md, section 4). No GTK, so it runs in
worker threads and in tests."""
import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime

NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
# CAP severity → DWD level 1–4; colours follow the level, the words are
# always shown too (colour is never the only carrier).
LEVELS = {"Minor": 1, "Moderate": 2, "Severe": 3, "Extreme": 4}
LEVEL_NAMES = {1: "Minor", 2: "Moderate", 3: "Severe", 4: "Extreme"}
# Altitudes in the file are feet; 9842.5197 ft (3000 m) means "all heights".
FEET = 0.3048
ALL_HEIGHTS_FT = 9842


@dataclass(frozen=True)
class Area:
    polygon: tuple                    # ((lat, lon), …)
    holes: tuple = ()                 # (((lat, lon), …), …)
    altitude_m: float = 0.0
    ceiling_m: float | None = None    # None: no upper limit

    def contains(self, latitude, longitude):
        return _inside(self.polygon, latitude, longitude) and not any(
            _inside(hole, latitude, longitude) for hole in self.holes)


@dataclass(frozen=True)
class Warning:
    identifier: str
    msg_type: str
    event: str
    severity: str
    urgency: str
    certainty: str
    headline: str
    description: str
    instruction: str
    sender: str
    onset: datetime | None
    expires: datetime | None
    colour: tuple | None              # DWD's AREA_COLOR (r, g, b)
    areas: tuple = ()
    names: tuple = field(default=(), compare=False)   # warn cell names
    references: tuple = field(default=(), compare=False)  # identifiers it updates

    @property
    def level(self):
        return LEVELS.get(self.severity, 0)

    @property
    def level_name(self):
        return LEVEL_NAMES.get(self.level, self.severity)

    def active(self, now):
        return self.expires is None or self.expires > now

    def areas_at(self, latitude, longitude):
        return [a for a in self.areas if a.contains(latitude, longitude)]


def _inside(polygon, latitude, longitude):
    """Even–odd ray casting in lat/lon; fine for areas of a few km."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if (yi > latitude) != (yj > latitude):
            x = xi + (latitude - yi) * (xj - xi) / (yj - yi)
            if longitude < x:
                inside = not inside
        j = i
    return inside


def _points(text):
    points = []
    for pair in text.split():
        lat, lon = pair.split(",")
        points.append((float(lat), float(lon)))
    return tuple(points)


def _time(text):
    return datetime.fromisoformat(text) if text else None


def _text(element, path):
    found = element.find(path, NS)
    return (found.text or "").strip() if found is not None else ""


def parse_alert(data):
    """One CAP XML document → Warning, or None for other statuses
    (tests, exercises) and cancellations."""
    root = ET.fromstring(data)
    if _text(root, "cap:status") != "Actual" or \
            _text(root, "cap:msgType") == "Cancel":
        return None
    info = root.find("cap:info", NS)
    if info is None:
        return None
    codes = {_text(c, "cap:valueName"): _text(c, "cap:value")
             for c in info.findall("cap:eventCode", NS)}
    colour = None
    if codes.get("AREA_COLOR"):
        try:
            colour = tuple(int(v) for v in codes["AREA_COLOR"].split())
        except ValueError:
            colour = None
    areas, names = [], []
    for area in info.findall("cap:area", NS):
        geocodes = {}
        for code in area.findall("cap:geocode", NS):
            geocodes.setdefault(_text(code, "cap:valueName"), []).append(
                _text(code, "cap:value"))
        altitude = float(_text(area, "cap:altitude") or 0) * FEET
        ceiling_ft = float(_text(area, "cap:ceiling") or ALL_HEIGHTS_FT)
        ceiling = None if ceiling_ft >= ALL_HEIGHTS_FT else ceiling_ft * FEET
        for polygon in area.findall("cap:polygon", NS):
            holes = tuple(_points(h) for h in geocodes.get("EXCLUDE_POLYGON", ()))
            areas.append(Area(_points(polygon.text or ""), holes,
                              altitude, ceiling))
        if "WARNCELLID" in geocodes:
            names.append(_text(area, "cap:areaDesc"))
    return Warning(
        identifier=_text(root, "cap:identifier"),
        msg_type=_text(root, "cap:msgType"),
        event=_text(info, "cap:event"),
        severity=_text(info, "cap:severity"),
        urgency=_text(info, "cap:urgency"),
        certainty=_text(info, "cap:certainty"),
        headline=_text(info, "cap:headline"),
        description=_text(info, "cap:description"),
        instruction=_text(info, "cap:instruction"),
        sender=_text(info, "cap:senderName"),
        onset=_time(_text(info, "cap:onset")),
        expires=_time(_text(info, "cap:expires")),
        colour=colour,
        areas=tuple(areas),
        names=tuple(names),
        references=tuple(ref.split(",")[1] for ref in
                         _text(root, "cap:references").split() if ref.count(",") >= 2))


def parse_zip(data):
    """The status zip (bytes) → list of Warnings."""
    warnings = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if name.endswith(".xml"):
                warning = parse_alert(archive.read(name))
                if warning is not None:
                    warnings.append(warning)
    return warnings


def at_point(warnings, latitude, longitude, now):
    """Active warnings whose polygons contain the point, most severe
    first, then by onset."""
    found = [w for w in warnings
             if w.active(now) and w.areas_at(latitude, longitude)]
    far_future = datetime.max.replace(tzinfo=now.tzinfo)
    return sorted(found, key=lambda w: (-w.level, w.onset or far_future))


def short(warnings):
    """One line for the places list and the nowcast: "Frost warning",
    "2 warnings: Icy surfaces, fog"."""
    if not warnings:
        return ""
    if len(warnings) == 1:
        return f"{warnings[0].event.capitalize()} warning"
    events = list(dict.fromkeys(w.event for w in warnings))
    text = ", ".join([events[0].capitalize()] + events[1:])
    return f"{len(warnings)} warnings: {text}"


def per_place(warnings, store, now):
    """{place id: short line} for every place of the store with a
    position and at least one warning."""
    model = store.model
    lines = {}
    for i in range(model.get_n_items()):
        place = model.get_item(i)
        if place.has_position:
            line = short(at_point(warnings, place.latitude, place.longitude, now))
            if line:
                lines[place.id] = line
    return lines
