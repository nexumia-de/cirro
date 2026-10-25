"""Decoder for one member of the DWD RV nowcast composite (ODIM HDF5).

Layout and units: docs/data-sources.md, section 1. Pure functions, no
GTK, so they are unit-tested with the recorded file in tests/data/.
"""
import io
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

# Raw values are narrowed to uint16 (largest value seen: 2333); this
# marks cells outside the radar coverage.
NODATA = 0xFFFF
# Values at or above this are clipped so they never collide with NODATA.
RAW_MAX = NODATA - 1


@dataclass(frozen=True)
class Grid:
    """Polar stereographic grid of the composite (row 0 is the north edge)."""
    projdef: str
    xsize: int
    ysize: int
    xscale: float
    yscale: float
    # Outer edges of the grid in projected metres.
    x_min: float
    y_max: float


@dataclass(frozen=True)
class Frame:
    raw: np.ndarray            # uint16, shape (ysize, xsize), NODATA outside
    gain: float
    offset: float              # mm per 5 min = raw * gain + offset
    undetect: int              # raw value meaning "no precipitation"
    analysis_time: datetime    # UTC
    valid_time: datetime       # UTC, end of the 5-min interval
    forecast: bool
    grid: Grid

    def mm_per_hour(self):
        """Rain rate in mm/h as float32, NaN outside the coverage."""
        rate = (self.raw.astype(np.float32) * self.gain + self.offset) * 12
        rate[self.raw == self.undetect] = 0
        rate[self.raw == NODATA] = np.nan
        return rate


def _str(value):
    return value.decode() if isinstance(value, bytes) else str(value)


def _time(date, time):
    return datetime.strptime(_str(date) + _str(time), "%Y%m%d%H%M%S") \
        .replace(tzinfo=timezone.utc)


def parse_projdef(projdef):
    """'+proj=stere +lat_0=90 …' → {'proj': 'stere', 'lat_0': 90.0, …}."""
    params = {}
    for token in projdef.split():
        key, _, value = token.lstrip("+").partition("=")
        try:
            params[key] = float(value)
        except ValueError:
            params[key] = value or True
    return params


def _open(data):
    import h5py

    source = io.BytesIO(data) if isinstance(data, (bytes, bytearray)) else data
    return h5py.File(source, "r")


def _times(f):
    """(analysis time, valid time, forecast flag) from the attributes."""
    dataset = f["dataset1/what"].attrs
    top = f["what"].attrs
    return (_time(top["date"], top["time"]),
            _time(dataset["enddate"], dataset["endtime"]),
            _str(f["how"].attrs.get("simulated", b"False")) == "True")


def peek(data):
    """(analysis time, valid time, forecast flag) of a member without
    decompressing its data, for the frame timeline."""
    with _open(data) as f:
        return _times(f)


def decode(data):
    """Decode one `composite_rv_<time>_<lead>-hd5` member (bytes or path)."""
    with _open(data) as f:
        what = f["dataset1/data1/what"].attrs
        quantity = _str(what["quantity"])
        if quantity != "ACRR":
            raise ValueError(f"unexpected quantity {quantity!r}")
        values = f["dataset1/data1/data"][()]
        nodata = int(what["nodata"])
        undetect = int(what["undetect"])

        raw = np.minimum(values, RAW_MAX).astype(np.uint16)
        raw[values == nodata] = NODATA

        where = f["where"].attrs
        projdef = _str(where["projdef"])
        xsize, ysize = int(where["xsize"]), int(where["ysize"])
        if values.shape != (ysize, xsize):
            raise ValueError(f"data shape {values.shape} does not match "
                             f"grid {ysize}×{xsize}")
        xscale, yscale = float(where["xscale"]), float(where["yscale"])
        # The corner coordinates are the outer cell edges; the upper-left
        # one fixes the grid's position (docs/data-sources.md).
        from cirro.projection import Stereographic
        x_min, y_max = Stereographic(parse_projdef(projdef)).forward(
            float(where["UL_lon"]), float(where["UL_lat"]))
        grid = Grid(projdef, xsize, ysize, xscale, yscale,
                    round(float(x_min), 1), round(float(y_max), 1))

        analysis_time, valid_time, forecast = _times(f)
        return Frame(
            raw=raw,
            gain=float(what["gain"]),
            offset=float(what["offset"]),
            undetect=undetect,
            analysis_time=analysis_time,
            valid_time=valid_time,
            forecast=forecast,
            grid=grid,
        )
