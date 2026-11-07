"""Legend entries of a layer from GeoServer's `GetLegendGraphic` JSON:
colour scales of raster layers, coloured classes of vector layers.
Cirro draws them itself (cirro/layers/legend.py), in English and in
theme colours; DWD's legend images are German, black on white."""
import re
from dataclasses import dataclass

_HEX = re.compile(r"#?([0-9a-fA-F]{6})")


@dataclass(frozen=True)
class Entry:
    color: tuple     # r, g, b (0 … 255)
    label: str


@dataclass(frozen=True)
class Legend:
    kind: str        # "scale" (raster intervals) or "classes"
    entries: tuple
    unit: str = ""


def _rgb(text):
    match = _HEX.fullmatch((text or "").strip())
    if not match:
        return None
    value = match[1]
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return f"{value:g}"


_FIRST_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
_UNIT = re.compile(r"(°C|mm|m/s|km/h|hPa|cm|m|%)\s*$")


def _clean(label):
    if isinstance(label, list):
        label = " ".join(str(part) for part in label)
    return " ".join(str(label or "").split())


def _bound(label, quantity):
    """Short label of a colour class: its lower bound, from DWD's label
    ("[0.1 ... 0.2)", "0.5-1.0 m", "< -60 °C", ">= 11") or else the
    quantity."""
    match = _FIRST_NUMBER.search(label)
    if match:
        number = f"{float(match[0].replace(',', '.')):g}"
        head = label[:match.start()].strip()
        if head.startswith("<"):
            return f"<{number}"
        if head.startswith(">"):
            return f"≥{number}" if "=" in head else f">{number}"
        return number
    return _number(quantity) or label


# DWD's unit labels in English; "?C" is how some layers send "°C".
UNITS = {"UV-Index (max)": "UV index", "hours": "h", "days": "days",
         "1/min * 100km²": "per min and 100 km²"}


def _unit(text):
    text = text.replace("?C", "°C")
    return UNITS.get(text, text)


def parse(data, translations=None):
    """`data` is the decoded JSON; `translations` maps DWD's German labels
    to English. Returns a Legend, or None if there is nothing to show."""
    translations = translations or {}
    scale, classes, unit = [], [], ""
    for legend in data.get("Legend", []):
        for rule in legend.get("rules", []):
            title = _clean(rule.get("title") or rule.get("name"))
            for symbolizer in rule.get("symbolizers", []):
                for kind, spec in symbolizer.items():
                    if kind == "Raster":
                        entries = (spec.get("colormap") or {}).get("entries", [])
                        for entry in entries:
                            color = _rgb(entry.get("color"))
                            label = _clean(entry.get("label"))
                            header = not scale and re.search(r"[a-zA-Z]{2}", label) \
                                and not _UNIT.search(label)
                            if header or str(entry.get("opacity", "1")) in ("0", "0.0"):
                                # The transparent or text-only first class
                                # names the unit.
                                if re.search(r"[a-zA-Z]", label):
                                    unit = unit or label
                                continue
                            if color is None:
                                continue
                            found = _UNIT.search(label)
                            if found and not unit:
                                unit = found[1]
                            scale.append(Entry(color, _bound(label, entry.get("quantity"))))
                    elif kind in ("Polygon", "Point", "Line") and title:
                        color = _rgb(spec.get("fill") or spec.get("stroke")
                                     or (spec.get("graphics") or [{}])[0].get("fill"))
                        if color is None:
                            continue
                        label = translations.get(title, title)
                        if all(e.label != label for e in classes):
                            classes.append(Entry(color, label))
    if scale:
        return Legend("scale", tuple(scale), _unit(unit))
    if classes:
        return Legend("classes", tuple(classes))
    return None


def thin(entries, count):
    """At most `count` labels for a scale: every n-th, the rest empty."""
    if len(entries) <= count:
        return [e.label for e in entries]
    every = -(-len(entries) // count)
    return [e.label if i % every == 0 else "" for i, e in enumerate(entries)]
