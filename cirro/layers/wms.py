"""Requests to DWD's GeoServer WMS (docs/data-sources.md, section 11).

No GTK, so it runs in worker threads. Every request sends the
`User-Agent`; capabilities are fetched per layer (≈ 11 KB, 3 KB
gzipped), not for the whole server (975 KB)."""
import gzip
import json
import logging
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from cirro import USER_AGENT
from cirro.layers.timeaxis import TimeAxis, format_time, parse_time

BASE_URL = "https://maps.dwd.de/geoserver/dwd/"
_WMS = "{http://www.opengis.net/wms}"

log = logging.getLogger(__name__)


def get(url, timeout=30):
    """GET `url` → (bytes, content type). Raises on HTTP errors."""
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        kind = response.headers.get("Content-Type", "")
    log.debug("%s: %d bytes in %.2f s", url[:160], len(body),
              time.monotonic() - started)
    return body, kind


class ServiceError(Exception):
    """GeoServer answered with a ServiceExceptionReport."""


def _check(body, kind):
    if "xml" in kind and b"ServiceException" in body[:600]:
        root = ET.fromstring(body)
        text = " ".join(t.strip() for t in root.itertext() if t.strip())
        raise ServiceError(text[:300])
    return body


def _query(params):
    return urllib.parse.urlencode(params, safe=":/,")


@dataclass(frozen=True)
class Capabilities:
    """What one layer accepts: its time axis (None for timeless layers)
    and the model run its images belong to."""
    axis: TimeAxis | None
    reference_time: str = ""


def capabilities_url(layer, base_url=BASE_URL):
    # GeoServer's per-layer virtual service.
    return (f"{base_url}{urllib.parse.quote(layer)}/wms?"
            + _query({"service": "WMS", "version": "1.3.0",
                      "request": "GetCapabilities"}))


def parse_capabilities(body, layer):
    root = ET.fromstring(body)
    for node in root.iter(f"{_WMS}Layer"):
        if node.findtext(f"{_WMS}Name") not in (layer, f"dwd:{layer}"):
            continue
        axis, reference = None, ""
        for dim in node.findall(f"{_WMS}Dimension"):
            name = dim.get("name", "").lower()
            if name == "time" and (dim.text or "").strip():
                axis = TimeAxis.parse(dim.text)
            elif name == "reference_time":
                # The newest run: the default is the oldest for some
                # ensemble layers (two days old on 2026-11-07).
                runs = [r.strip() for r in (dim.text or "").split(",") if r.strip()]
                reference = max(runs, default=dim.get("default") or "")
        return Capabilities(axis, reference)
    raise ValueError(f"layer {layer} not in capabilities")


def fetch_capabilities(layer, base_url=BASE_URL):
    body, kind = get(capabilities_url(layer, base_url))
    return parse_capabilities(_check(body, kind), layer)


def _dims(params, dims):
    # GeoServer's custom dimensions: DIM_<NAME>=value.
    for name, value in dims:
        params[f"dim_{name.lower()}"] = value


def map_url(layers, bbox, size, time_=None, style=None, cql="",
            reference_time="", dims=(), base_url=BASE_URL):
    """GetMap for EPSG:3857 `bbox` (west, south, east, north in metres)
    and `size` (width, height) in pixels."""
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": ",".join(f"dwd:{name}" for name in layers),
        "styles": ",".join([style or ""] * len(layers)),
        "crs": "EPSG:3857",
        "bbox": ",".join(f"{v:.0f}" for v in bbox),
        "width": size[0], "height": size[1],
        "format": "image/png", "transparent": "true",
    }
    if time_ is not None:
        params["time"] = format_time(time_)
    if reference_time:
        params["dim_reference_time"] = reference_time
    if cql:
        params["cql_filter"] = ";".join([cql] * len(layers))
    _dims(params, dims)
    return f"{base_url}wms?" + _query(params)


def fetch_map(url):
    """PNG bytes of a GetMap URL."""
    body, kind = get(url)
    _check(body, kind)
    if not body.startswith(b"\x89PNG"):
        raise ServiceError(f"not a PNG ({kind})")
    return body


def legend_url(layer, style=None, base_url=BASE_URL):
    params = {"service": "WMS", "version": "1.3.0",
              "request": "GetLegendGraphic", "format": "application/json",
              "layer": f"dwd:{layer}"}
    if style:
        params["style"] = style
    return f"{base_url}wms?" + _query(params)


def fetch_legend(layer, style=None, base_url=BASE_URL):
    body, kind = get(legend_url(layer, style, base_url))
    return json.loads(_check(body, kind))


def feature_info_url(layers, latitude, longitude, time_=None, cql="",
                     reference_time="", fields=(), dims=(), base_url=BASE_URL):
    """GetFeatureInfo at one point: a 3×3 pixel map around it, queried in
    the middle."""
    d = 0.01
    names = ",".join(f"dwd:{name}" for name in layers)
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetFeatureInfo",
        "layers": names, "query_layers": names, "styles": "",
        "crs": "EPSG:4326",
        # WMS 1.3.0 with EPSG:4326: latitude first.
        "bbox": f"{latitude - d},{longitude - d},{latitude + d},{longitude + d}",
        "width": 3, "height": 3, "i": 1, "j": 1,
        "info_format": "application/json", "feature_count": 10,
    }
    if fields:
        params["propertyName"] = ",".join(fields)
    _dims(params, dims)
    if time_ is not None:
        params["time"] = format_time(time_)
    if reference_time:
        params["dim_reference_time"] = reference_time
    if cql:
        params["cql_filter"] = ";".join([cql] * len(layers))
    return f"{base_url}wms?" + _query(params)


def fetch_feature_info(url):
    body, kind = get(url)
    return json.loads(_check(body, kind)).get("features", [])


__all__ = ["Capabilities", "ServiceError", "fetch_capabilities", "fetch_map",
           "fetch_legend", "fetch_feature_info", "map_url", "legend_url",
           "feature_info_url", "parse_capabilities", "parse_time"]
