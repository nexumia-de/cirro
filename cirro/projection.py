"""Map projections for the radar overlay, in numpy (no pyproj in the Flatpak).

The RV grid is polar stereographic; the map is Web Mercator. The radar
texture is reprojected once per grid definition into a Mercator-aligned
index table, then every frame is a single numpy gather
(docs/radar-architecture.md, step 5).
"""
import math
from dataclasses import dataclass

import numpy as np

# Web Mercator clamps latitudes like libshumate does.
MAX_LATITUDE = 85.0511287798


class Stereographic:
    """Ellipsoidal north-polar stereographic projection (Snyder 1987, 21-33)."""

    def __init__(self, params):
        if params.get("proj") != "stere" or params.get("lat_0") != 90:
            raise ValueError(f"unsupported projection {params!r}")
        a = params["a"]
        b = params.get("b", a)
        self.a = a
        self.e = math.sqrt(1 - (b / a) ** 2)
        self.lon_0 = math.radians(params.get("lon_0", 0))
        self.x_0 = params.get("x_0", 0)
        self.y_0 = params.get("y_0", 0)
        lat_ts = math.radians(params.get("lat_ts", 90))
        m_c = math.cos(lat_ts) / math.sqrt(1 - (self.e * math.sin(lat_ts)) ** 2)
        self.k = a * m_c / self._t(lat_ts)

    def _t(self, phi):
        e_sin = self.e * np.sin(phi)
        return np.tan(np.pi / 4 - phi / 2) / ((1 - e_sin) / (1 + e_sin)) ** (self.e / 2)

    def forward(self, lon, lat):
        """Degrees → projected metres (scalars or arrays)."""
        lam = np.radians(lon) - self.lon_0
        rho = self.k * self._t(np.radians(lat))
        return self.x_0 + rho * np.sin(lam), self.y_0 - rho * np.cos(lam)


def mercator_xy(lon, lat):
    """Degrees → normalised Web Mercator, x and y in [0, 1], y down."""
    lat = np.clip(lat, -MAX_LATITUDE, MAX_LATITUDE)
    s = np.sin(np.radians(lat))
    return (np.asarray(lon) + 180) / 360, 0.5 - np.log((1 + s) / (1 - s)) / (4 * np.pi)


def mercator_lonlat(x, y):
    """Normalised Web Mercator → degrees."""
    return np.asarray(x) * 360 - 180, np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(y)))))


@dataclass(frozen=True)
class Reprojection:
    """Maps a Mercator-aligned target image to source grid cells.

    `index[i]` is the flat index of the source cell for target pixel i, or
    the source size (one past the end) for pixels outside the grid, so a
    gather from the source with one appended NODATA value yields the
    target image.
    """
    width: int
    height: int
    # Bounds in degrees (north, west, south, east): the image's edges.
    north: float
    west: float
    south: float
    east: float
    index: np.ndarray

    def apply(self, values, fill):
        flat = np.append(values.ravel(), np.asarray(fill, values.dtype))
        return flat[self.index].reshape(self.height, self.width)


def reproject_grid(grid, width=1400, block_rows=128):
    """Build the Reprojection for a radar Grid at `width` target pixels."""
    from cirro.radar import parse_projdef

    stere = Stereographic(parse_projdef(grid.projdef))
    xs = grid.x_min + np.arange(grid.xsize + 1) * grid.xscale
    ys = grid.y_max - np.arange(grid.ysize + 1) * grid.yscale

    # Bounding box of the grid outline in Mercator: walk its four edges.
    edge_x = np.concatenate([xs, np.full(ys.size, xs[-1]), xs[::-1], np.full(ys.size, xs[0])])
    edge_y = np.concatenate([np.full(xs.size, ys[0]), ys, np.full(xs.size, ys[-1]), ys[::-1]])
    lon, lat = stere_inverse(stere, edge_x, edge_y)
    mx, my = mercator_xy(lon, lat)
    x0, x1, y0, y1 = mx.min(), mx.max(), my.min(), my.max()
    height = max(1, round(width * (y1 - y0) / (x1 - x0)))

    # Pixel centres of the target image → source cell, in blocks of rows
    # so the float64 temporaries stay small (a phone has little memory).
    tx = x0 + (np.arange(width) + 0.5) * (x1 - x0) / width
    ty = y0 + (np.arange(height) + 0.5) * (y1 - y0) / height
    index = np.empty((height, width), dtype=np.int32)
    for start in range(0, height, block_rows):
        rows = slice(start, start + block_rows)
        tlon, tlat = mercator_lonlat(*np.meshgrid(tx, ty[rows]))
        sx, sy = stere.forward(tlon, tlat)
        col = np.floor((sx - grid.x_min) / grid.xscale).astype(np.int64)
        row = np.floor((grid.y_max - sy) / grid.yscale).astype(np.int64)
        inside = (col >= 0) & (col < grid.xsize) & (row >= 0) & (row < grid.ysize)
        index[rows] = np.where(inside, row * grid.xsize + col,
                               grid.xsize * grid.ysize)

    west, north = mercator_lonlat(x0, y0)
    east, south = mercator_lonlat(x1, y1)
    return Reprojection(width, height, float(north), float(west), float(south),
                        float(east), index.ravel())


def stere_inverse(stere, x, y, iterations=8):
    """Projected metres → degrees, by fixed-point iteration on latitude."""
    dx = np.asarray(x, dtype=np.float64) - stere.x_0
    dy = stere.y_0 - np.asarray(y, dtype=np.float64)
    rho = np.hypot(dx, dy)
    t = rho / stere.k
    lon = np.degrees(stere.lon_0 + np.arctan2(dx, dy))
    phi = np.pi / 2 - 2 * np.arctan(t)
    for _ in range(iterations):
        e_sin = stere.e * np.sin(phi)
        phi = np.pi / 2 - 2 * np.arctan(t * ((1 - e_sin) / (1 + e_sin)) ** (stere.e / 2))
    return lon, np.degrees(phi)
