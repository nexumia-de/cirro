"""The text shown for a tap on the map: the layer's value at that point,
from GetFeatureInfo features (docs/map-layers.md)."""
import math

from cirro import wind
from cirro.layers.catalogue import POLLEN_LEVELS

_SKIP = {"TIME", "REFERENCE_TIME", "ELEVATION", "ENSEMBLE_PRODUCT"}
_SEVERITY = {"Minor": "level 1", "Moderate": "level 2", "Severe": "level 3",
             "Extreme": "level 4"}
_HEALTH = {"positiver Einfluss": "positive effect",
           "kein Einfluss": "no effect",
           "geringe Gefährdung": "low risk", "hohe Gefährdung": "high risk"}
compass = wind.compass


def _numbers(properties):
    for name, value in properties.items():
        if name in _SKIP:
            continue
        try:
            yield name, float(value)
        except (TypeError, ValueError):
            continue


def _number(features, value):
    for feature in features:
        for _, number in _numbers(feature.get("properties", {})):
            if math.isnan(number):
                continue
            text = f"{number:.{value.decimals}f}"
            return f"{text} {value.unit}".strip()
    return None


def _wind(features):
    for feature in features:
        p = feature.get("properties", {})
        try:
            u, v = float(p["u"]), float(p["v"])
        except (KeyError, TypeError, ValueError):
            continue
        speed = math.hypot(u, v)
        # u, v point where the wind blows to; direction is where it comes from.
        direction = (math.degrees(math.atan2(-u, -v)) + 360) % 360
        return f"{speed:.1f} m/s from {compass(direction)}"
    return None


def _warnings(features):
    texts = []
    for feature in features:
        p = feature.get("properties", {})
        event = str(p.get("EVENT", "")).strip()
        if not event:
            continue
        level = _SEVERITY.get(p.get("SEVERITY"), "")
        text = event.capitalize() + (f", {level}" if level else "")
        if text not in texts:
            texts.append(text)
    return "; ".join(texts) if texts else "No warning"


def _pollen(features):
    for feature in features:
        p = feature.get("properties", {})
        try:
            level = POLLEN_LEVELS[int(p.get("POLLENINT"))]
        except (TypeError, ValueError, IndexError):
            continue
        region = str(p.get("GEN", "")).strip()
        return level.capitalize() + (f" · {region}" if region else "")
    return None


def _health(features):
    for feature in features:
        p = feature.get("properties", {})
        value = str(p.get("PARAMETER_VALUE", "")).strip()
        if value:
            return _HEALTH.get(value, value).capitalize()
    return None


def describe(value, features):
    """Text for `features` read as `value` (catalogue.Value), or None."""
    if value is None:
        return None
    if value.kind == "number":
        return _number(features, value)
    if value.kind == "wind":
        return _wind(features)
    if value.kind == "warning":
        return _warnings(features)
    if value.kind == "pollen":
        return _pollen(features)
    if value.kind == "health":
        return _health(features)
    return None


def station_text(value, stations, latitude, longitude, within_km=30):
    """Text of the nearest station within `within_km` (station layers),
    or None."""
    from cirro.layers.wfs import nearest
    station, _ = nearest(stations, latitude, longitude, within_km)
    if station is None:
        return None
    if value.kind == "wind":
        text = wind.describe(station.value, station.direction)
    else:
        text = f"{station.value:.{value.decimals}f} {value.unit}".strip()
    return f"{text}, {station.name}"
