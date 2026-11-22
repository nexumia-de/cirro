"""Decoder for DMI's radar composite (ODIM_H5 2.0, issue #11).

Reflectivity (DBZH, uint8) on a 500 m oblique stereographic grid,
converted to a rain rate with the Z-R relation in the file and stored
in the same `radar.Frame` as the DWD composite, so drawing, colouring
and sampling stay the same (docs/data-sources.md, section 8). No GTK."""

import math
from datetime import UTC, datetime

import numpy as np

from cirro import radar

# Raw unit of the converted frame: mm per 5 min, like DWD's RV.
GAIN = 0.001


def is_dmi(f):
    """Whether an open HDF5 file is a DMI composite (quantity DBZH)."""
    group = f.get("dataset1/data1")
    return group is not None and radar._str(group.attrs.get("quantity", b"")) == "DBZH"


def rate(dbz, a=200.0, b=1.6):
    """Rain rate in mm/h from reflectivity, Z = a·R^b."""
    return (10 ** (np.asarray(dbz, dtype=np.float64) / 10) / a) ** (1 / b)


def _table(f):
    """uint8 code → raw value of the converted frame (256 entries)."""
    what = f["what"].attrs
    how = f["how"].attrs
    gain, offset = float(what["gain"]), float(what["offset"])
    nodata, undetect = int(what["nodata"]), int(what["undetect"])
    a = float(np.ravel(how.get("zr-a", [200.0]))[0])
    b = float(np.ravel(how.get("zr-b", [1.6]))[0])
    codes = np.arange(256)
    mm_5min = rate(codes * gain + offset, a, b) / 12
    table = np.minimum(np.round(mm_5min / GAIN), radar.RAW_MAX).astype(np.uint16)
    table[undetect] = 0
    table[nodata] = radar.NODATA
    return table


def _time(f):
    what = f["what"].attrs
    stamp = radar._str(what["date"]) + radar._str(what["time"])[:4]
    return datetime.strptime(stamp, "%Y%m%d%H%M").replace(tzinfo=UTC)


def _grid(f, shape):
    where = f["where"].attrs
    projdef = radar._str(where["projdef"])
    from cirro.projection import stereographic

    xscale, yscale = float(where["xscale"]), float(where["yscale"])
    ul_x, ul_y = stereographic(radar.parse_projdef(projdef)).forward(
        float(np.ravel(where["UL_lon"])[0]), float(np.ravel(where["UL_lat"])[0])
    )
    # UL and LR lie (n - 1) cells apart: the corners are cell centres.
    return radar.Grid(
        projdef=projdef,
        xsize=shape[1],
        ysize=shape[0],
        xscale=xscale,
        yscale=yscale,
        x_min=float(ul_x) - xscale / 2,
        y_max=float(ul_y) + yscale / 2,
    )


def peek(f):
    """(analysis time, valid time, forecast flag): the scan time; DMI has
    no forecast."""
    time_ = _time(f)
    return time_, time_, False


def decode(f):
    codes = f["dataset1/data1/data"][()]
    time_ = _time(f)
    return radar.Frame(
        raw=_table(f)[codes],
        gain=GAIN,
        offset=0.0,
        undetect=0,
        analysis_time=time_,
        valid_time=time_,
        forecast=False,
        grid=_grid(f, codes.shape),
    )


def sample_points(f, points):
    """Rain rates in mm/h at (latitude, longitude) points, NaN outside."""
    frame = decode(f)
    rates = []
    for latitude, longitude in points:
        where = radar.cell(frame.grid, latitude, longitude)
        value = int(frame.raw[where]) if where is not None else radar.NODATA
        rates.append(math.nan if value == radar.NODATA else value * GAIN * 12)
    return rates
