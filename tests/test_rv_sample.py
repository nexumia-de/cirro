"""Pins the RV composite layout recorded in docs/data-sources.md.

Uses a real member recorded from composite_rv_20261024_2110.tar. If DWD
changes the format again, record a new file and update the docs.
"""
from pathlib import Path

import pytest

h5py = pytest.importorskip("h5py")

SAMPLE = Path(__file__).parent / "data" / "composite_rv_20261024_2110_000-hd5"


@pytest.fixture
def rv():
    with h5py.File(SAMPLE, "r") as f:
        yield f


def test_odim_layout(rv):
    assert rv.attrs["Conventions"] == b"ODIM_H5/V2_3"
    assert rv["what"].attrs["object"] == b"COMP"
    data = rv["dataset1/data1/data"]
    assert data.dtype == "uint32"
    assert data.shape == (1200, 1100)
    what = rv["dataset1/data1/what"].attrs
    assert what["quantity"] == b"ACRR"
    assert what["gain"] == pytest.approx(0.001)
    assert what["offset"] == pytest.approx(-0.001)
    assert what["nodata"] == 2**32 - 1
    assert what["undetect"] == 0


def test_grid_definition(rv):
    where = rv["where"].attrs
    assert where["xsize"] == 1100 and where["ysize"] == 1200
    assert where["xscale"] == 1000 and where["yscale"] == 1000
    assert where["projdef"].startswith(b"+proj=stere +lat_ts=60 +lat_0=90 +lon_0=10 ")
    assert where["UL_lat"] == pytest.approx(55.862, abs=1e-3)
    assert where["LR_lon"] == pytest.approx(16.581, abs=1e-3)


def test_analysis_and_valid_time(rv):
    assert (rv["what"].attrs["date"], rv["what"].attrs["time"]) == (b"20261024", b"211000")
    what = rv["dataset1/what"].attrs
    assert (what["startdate"], what["starttime"]) == (b"20261024", b"210500")
    assert (what["enddate"], what["endtime"]) == (b"20261024", b"211000")
    assert rv["how"].attrs["simulated"] == b"False"
