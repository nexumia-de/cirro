"""Station measurements from DWD's GeoServer WFS (`dwd:RBSN_*`): 72
stations, one hour (or day) per request, about 21 KB of GeoJSON
(docs/data-sources.md, section 10). No GTK."""
import json
import math
import urllib.parse
from dataclasses import dataclass

from cirro.layers.wms import BASE_URL, _check, get


@dataclass(frozen=True)
class Station:
    name: str
    latitude: float
    longitude: float
    value: float
    direction: float | None = None   # wind: where it comes from, degrees


def features_url(typename, time_, base_url=BASE_URL):
    params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
              "typeNames": f"dwd:{typename}",
              "outputFormat": "application/json"}
    if time_ is not None:
        stamp = time_.strftime("%Y-%m-%dT%H:%M:%SZ")
        params["CQL_FILTER"] = f"M_DATE='{stamp}'"
    return f"{base_url}ows?" + urllib.parse.urlencode(params, safe=":/'")


def parse(data, field):
    """Stations with a number in `field` (and DIRECTION for wind)."""
    stations = []
    for feature in data.get("features", []):
        p = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        try:
            longitude, latitude = geometry["coordinates"][:2]
            value = float(p[field])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isnan(value):
            continue
        direction = p.get("DIRECTION")
        try:
            direction = float(direction) if direction is not None else None
        except (TypeError, ValueError):
            direction = None
        stations.append(Station(str(p.get("NAME", "")).strip(), latitude,
                                longitude, value, direction))
    return stations


def fetch(typename, field, time_, base_url=BASE_URL):
    body, kind = get(features_url(typename, time_, base_url))
    return parse(json.loads(_check(body, kind)), field)


def distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def nearest(stations, latitude, longitude, within_km=None):
    """(station, distance in km) closest to a point, or (None, None)."""
    best = min(stations, default=None,
               key=lambda s: distance_km(latitude, longitude, s.latitude, s.longitude))
    if best is None:
        return None, None
    km = distance_km(latitude, longitude, best.latitude, best.longitude)
    if within_km is not None and km > within_km:
        return None, None
    return best, km
