"""The map area a layer image is requested for: the visible part of the
libshumate map in Web Mercator (EPSG:3857) and its corners in degrees,
which the texture layer draws at (cirro/radar_layer.py)."""
import math
from dataclasses import dataclass

RADIUS = 6378137.0
HALF = math.pi * RADIUS
TILE = 256
MAX_LATITUDE = 85.0511
# Requests stay below this many pixels per side (bandwidth on the phone).
MAX_PIXELS = 1280


def to_mercator(latitude, longitude):
    latitude = max(-MAX_LATITUDE, min(MAX_LATITUDE, latitude))
    x = math.radians(longitude) * RADIUS
    y = math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2)) * RADIUS
    return x, y


def from_mercator(x, y):
    longitude = math.degrees(x / RADIUS)
    latitude = math.degrees(2 * math.atan(math.exp(y / RADIUS)) - math.pi / 2)
    return latitude, longitude


@dataclass(frozen=True)
class View:
    bbox: tuple    # west, south, east, north in metres
    size: tuple    # width, height in pixels

    @property
    def bounds(self):
        """(north, west, south, east) in degrees."""
        west, south, east, north = self.bbox
        n, w = from_mercator(west, north)
        s, e = from_mercator(east, south)
        return n, w, s, e


def view(latitude, longitude, zoom, width, height, scale=1, rotation=0.0):
    """The area of a `width` × `height` widget showing the map centred
    on (`latitude`, `longitude`) at `zoom`. A rotated map gets the
    square around its diagonal, so the corners are covered too."""
    if rotation:
        width = height = math.hypot(width, height)
    metres_per_pixel = 2 * HALF / (TILE * 2 ** zoom)
    cx, cy = to_mercator(latitude, longitude)
    half_w, half_h = width / 2 * metres_per_pixel, height / 2 * metres_per_pixel
    west, east = cx - half_w, cx + half_w
    south = max(cy - half_h, -HALF)
    north = min(cy + half_h, HALF)
    pixels_w, pixels_h = width * scale, height * scale * (north - south) / (2 * half_h)
    shrink = min(1.0, MAX_PIXELS / max(pixels_w, pixels_h, 1))
    size = (max(1, round(pixels_w * shrink)), max(1, round(pixels_h * shrink)))
    return View((west, south, east, north), size)
