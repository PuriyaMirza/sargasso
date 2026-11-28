"""Helpers shared by the tests: synthetic frames, so no test touches the network."""

from datetime import datetime, timezone

import netCDF4
import numpy as np
import pytest

from sargasso_pipeline import grid, sources

# Tests narrow sources.SERVERS with monkeypatch; keep the real list at hand.
sources.SERVERS_ORIGINAL = list(sources.SERVERS)

FRAME_TIME = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)

# A small grid with the real region's edges: 0 to 38 N, 98 to 38 W.
SMALL_LAT = np.linspace(0.0, 38.0, 77)  # 0.5 degree rows
SMALL_LON = np.linspace(-98.0, -38.0, 61)  # 1 degree columns


def make_frame(lat=SMALL_LAT, lon=SMALL_LON, afai=None, when=FRAME_TIME):
    if afai is None:
        afai = np.full((lat.size, lon.size), -0.001)
    return grid.Frame(lat=lat, lon=lon, afai=afai, time=when)


def netcdf_bytes(tmp_path, lat=SMALL_LAT, lon=SMALL_LON, afai=None, when=FRAME_TIME,
                 dims=("time", "latitude", "longitude")):
    """Write a NetCDF file shaped like ERDDAP's and return its bytes."""
    if afai is None:
        afai = np.full((lat.size, lon.size), -0.001)
    path = tmp_path / "frame.nc"
    with netCDF4.Dataset(path, "w", format="NETCDF3_64BIT_OFFSET") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("latitude", lat.size)
        ds.createDimension("longitude", lon.size)
        ds.createVariable("time", "f8", ("time",))[:] = [when.timestamp()]
        ds.createVariable("latitude", "f8", ("latitude",))[:] = lat
        ds.createVariable("longitude", "f8", ("longitude",))[:] = lon
        var = ds.createVariable("AFAI", "f4", dims, fill_value=np.float32("nan"))
        data = afai[np.newaxis, :, :]
        if dims != ("time", "latitude", "longitude"):
            data = np.transpose(data, (0, 2, 1))
        var[:] = data
    return path.read_bytes()


@pytest.fixture
def frame_bytes(tmp_path):
    return netcdf_bytes(tmp_path)
