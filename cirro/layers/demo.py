"""Recorded GeoServer answers for store screenshots (issue #74).

With `CIRRO_DEMO_DATA` set and a `layers/` directory in it, every WMS
request is answered from recorded files instead of the server, the
layers' "now" is the recording time and images cover one recorded area,
whatever the map shows (docs/map-layers.md, demo mode). Never used for
live data."""
import json
import os
import urllib.parse
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from cirro.layers.geometry import View


@cache
def directory():
    root = os.environ.get("CIRRO_DEMO_DATA")
    path = Path(root) / "layers" if root else None
    return path if path and path.is_dir() else None


def active():
    return directory() is not None


@cache
def _recorded():
    return json.loads((directory() / "recorded.json").read_text())


def now():
    """The layers' "now": the recording time in demo mode."""
    if not active():
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(_recorded()["time"])


def view():
    """The recorded image area (EPSG:3857 bbox and size)."""
    recorded = _recorded()
    return View(tuple(recorded["bbox"]), tuple(recorded["size"]))


def stamp(text):
    """WMS time "2026-11-22T05:00:00.000Z" → "20261122T0500"."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")) \
        .astimezone(timezone.utc).strftime("%Y%m%dT%H%M")


def file_for(url):
    """Name of the recorded file answering a WMS URL."""
    parts = urllib.parse.urlsplit(url)
    query = {k.lower(): v for k, v in urllib.parse.parse_qsl(parts.query)}
    request = query.get("request", "")
    if request == "GetCapabilities":
        layer = parts.path.rstrip("/").split("/")[-2]
        return f"caps-{layer}.xml"
    if request == "GetLegendGraphic":
        return f"legend-{query['layer'].removeprefix('dwd:')}.json"
    if request == "GetMap":
        layers = query["layers"].replace("dwd:", "")
        when = f"-{stamp(query['time'])}" if "time" in query else ""
        return f"map-{layers}{when}.png"
    raise FileNotFoundError(f"no recorded answer for {request}")


def get(url):
    """(bytes, content type) of the recorded answer, like `wms.get`."""
    name = file_for(url)
    kinds = {".xml": "text/xml", ".json": "application/json", ".png": "image/png"}
    return (directory() / name).read_bytes(), kinds[Path(name).suffix]
