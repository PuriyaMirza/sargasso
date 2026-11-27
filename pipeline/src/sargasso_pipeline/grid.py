"""Read a frame and reshape it for the map.

MapLibre draws an image as a straight rectangle between its corners in Web
Mercator, the projection web maps use. In Web Mercator, a degree of latitude
gets taller the further you go from the equator. Our data rows are evenly
spaced in degrees, so before saving the image we pick rows that are evenly
spaced in Mercator instead. Otherwise the picture would drift off the
coastlines toward the north.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import netCDF4
import numpy as np

from . import sources


@dataclass
class Frame:
    lat: np.ndarray  # cell centres, ascending (south to north), degrees
    lon: np.ndarray  # cell centres, ascending (west to east), degrees, negative = west
    afai: np.ndarray  # shape (len(lat), len(lon)); NaN means no data
    time: datetime  # UTC


@dataclass
class Bounds:
    west: float
    south: float
    east: float
    north: float


def read_frame(netcdf_bytes):
    """Read a one-time-step AFAI frame from ERDDAP's NetCDF bytes and check its axes."""
    try:
        ds = netCDF4.Dataset("frame.nc", memory=netcdf_bytes)
    except OSError as err:
        raise ValueError(f"Couldn't read the downloaded NetCDF file ({err})") from err
    with ds:
        var = ds[sources.VARIABLE]
        if var.dimensions != ("time", "latitude", "longitude"):
            raise ValueError(f"Unexpected axis order {var.dimensions}")
        lat = np.asarray(ds["latitude"][:], dtype=np.float64)
        lon = np.asarray(ds["longitude"][:], dtype=np.float64)
        # netCDF4 hides fill values behind a mask; turn them into NaN.
        afai = np.ma.filled(var[0, :, :].astype(np.float64), np.nan)
        seconds = float(ds["time"][0])
    when = datetime.fromtimestamp(seconds, tz=timezone.utc)
    frame = Frame(lat=lat, lon=lon, afai=afai, time=when)
    check_frame(frame)
    return frame


def check_frame(frame):
    """Stop with a clear error if the frame isn't what we expect."""
    if frame.afai.shape != (frame.lat.size, frame.lon.size):
        raise ValueError(f"Data shape {frame.afai.shape} doesn't match the axes")
    if not (np.all(np.diff(frame.lat) > 0) and np.all(np.diff(frame.lon) > 0)):
        raise ValueError("Latitude and longitude must both ascend")
    near = lambda a, b: abs(a - b) < 0.1  # within a tenth of a degree
    if not (near(frame.lat[0], sources.LAT_MIN) and near(frame.lat[-1], sources.LAT_MAX)):
        raise ValueError(f"Latitude runs {frame.lat[0]} to {frame.lat[-1]}, expected 0 to 38")
    if not (near(frame.lon[0], sources.LON_MIN) and near(frame.lon[-1], sources.LON_MAX)):
        raise ValueError(f"Longitude runs {frame.lon[0]} to {frame.lon[-1]}, expected -98 to -38")
    if not np.isfinite(frame.afai).any():
        raise ValueError("The frame has no data at all")


def mercator_y(lat_deg):
    """Web Mercator y (in radians) for a latitude in degrees."""
    return np.log(np.tan(np.pi / 4 + np.radians(lat_deg) / 2))


def latitude_from_mercator_y(y):
    """The inverse of mercator_y."""
    return np.degrees(2 * np.arctan(np.exp(y)) - np.pi / 2)


def to_mercator_rows(frame):
    """Return (image, bounds): a north-up copy of the data whose rows are evenly
    spaced in Web Mercator, and the image's outer corners in degrees.

    Each output row copies the nearest data row (no blending), so no-data
    pixels stay no-data and values are never invented.
    """
    lat, lon = frame.lat, frame.lon
    dlat = (lat[-1] - lat[0]) / (lat.size - 1)  # spacing between row centres
    dlon = (lon[-1] - lon[0]) / (lon.size - 1)

    # The image's outer edges are half a cell beyond the outermost centres.
    bounds = Bounds(
        west=lon[0] - dlon / 2,
        south=lat[0] - dlat / 2,
        east=lon[-1] + dlon / 2,
        north=lat[-1] + dlat / 2,
    )
    y_south, y_north = mercator_y(bounds.south), mercator_y(bounds.north)

    # Data rows are shortest in Mercator near the equator. Make every output
    # row at least that short, so no data row is ever skipped. Northern rows
    # may repeat, which costs almost nothing after PNG compression.
    row_heights = mercator_y(lat + dlat / 2) - mercator_y(lat - dlat / 2)
    n_rows = math.ceil((y_north - y_south) / row_heights.min())

    # Centre of each output row, from the top (north) down.
    step = (y_north - y_south) / n_rows
    centres = latitude_from_mercator_y(y_north - (np.arange(n_rows) + 0.5) * step)

    # For each centre, pick the nearest data row.
    i = np.clip(np.searchsorted(lat, centres), 1, lat.size - 1)
    i = np.where(centres - lat[i - 1] < lat[i] - centres, i - 1, i)
    return frame.afai[i, :], bounds
