"""Axis order and Web Mercator resampling."""

import math

import numpy as np
import pytest

from conftest import SMALL_LAT, SMALL_LON, make_frame, netcdf_bytes
from sargasso_pipeline import grid


# --- Reading frames and checking axis order ---------------------------------

def test_read_frame_keeps_ascending_axes_and_turns_fill_into_nan(tmp_path):
    afai = np.full((SMALL_LAT.size, SMALL_LON.size), -0.001)
    afai[0, 0] = np.nan  # a no-data cell in the south-west corner
    afai[-1, -1] = 0.002  # a value in the north-east corner
    frame = grid.read_frame(netcdf_bytes(tmp_path, afai=afai))

    assert frame.lat[0] == 0.0 and frame.lat[-1] == 38.0
    assert frame.lon[0] == -98.0 and frame.lon[-1] == -38.0
    assert np.isnan(frame.afai[0, 0])
    assert frame.afai[-1, -1] == pytest.approx(0.002)
    assert frame.time.isoformat() == "2026-11-25T12:00:00+00:00"


def test_read_frame_rejects_swapped_axes(tmp_path):
    data = netcdf_bytes(tmp_path, dims=("time", "longitude", "latitude"))
    with pytest.raises(ValueError, match="axis order"):
        grid.read_frame(data)


def test_check_frame_rejects_descending_latitude():
    frame = make_frame(lat=SMALL_LAT[::-1])
    with pytest.raises(ValueError, match="ascend"):
        grid.check_frame(frame)


def test_check_frame_rejects_wrong_region():
    frame = make_frame(lon=SMALL_LON + 360)  # 262 to 322 east instead of -98 to -38
    with pytest.raises(ValueError, match="Longitude"):
        grid.check_frame(frame)


def test_check_frame_rejects_an_empty_frame():
    frame = make_frame(afai=np.full((SMALL_LAT.size, SMALL_LON.size), np.nan))
    with pytest.raises(ValueError, match="no data"):
        grid.check_frame(frame)


# --- Web Mercator resampling --------------------------------------------------

def merc(lat):
    """Web Mercator y, written out independently of grid.py."""
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def inverse_merc(y):
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def lat_marked_frame():
    """Each data row holds its own latitude, so we can see which row went where."""
    afai = np.repeat(SMALL_LAT[:, np.newaxis], SMALL_LON.size, axis=1)
    return make_frame(afai=afai)


def test_image_is_north_up_and_bounds_are_cell_edges():
    image, bounds = grid.to_mercator_rows(lat_marked_frame())
    assert image[0, 0] == 38.0  # top row is the northernmost data row
    assert image[-1, 0] == 0.0  # bottom row is the southernmost
    assert np.all(np.diff(image[:, 0]) <= 0)  # latitude only falls going down
    half_row, half_col = 0.25, 0.5
    assert bounds.south == pytest.approx(0.0 - half_row)
    assert bounds.north == pytest.approx(38.0 + half_row)
    assert bounds.west == pytest.approx(-98.0 - half_col)
    assert bounds.east == pytest.approx(-38.0 + half_col)


def test_each_image_row_holds_the_data_row_nearest_its_mercator_position():
    image, bounds = grid.to_mercator_rows(lat_marked_frame())
    y_top, y_bottom = merc(bounds.north), merc(bounds.south)
    n = image.shape[0]
    for row in range(n):
        centre_lat = inverse_merc(y_top - (row + 0.5) * (y_top - y_bottom) / n)
        nearest = SMALL_LAT[np.argmin(np.abs(SMALL_LAT - centre_lat))]
        assert image[row, 0] == nearest


def test_no_data_row_is_skipped():
    image, _ = grid.to_mercator_rows(lat_marked_frame())
    assert set(np.unique(image[:, 0])) == set(SMALL_LAT)


def test_a_point_lands_on_the_right_image_row():
    # Mark the cell nearest Barbados (13.1 N, 59.6 W), then check that the
    # image row it lands on spans 13.1 N when the image is stretched between
    # its corners in Web Mercator, which is how MapLibre draws it.
    afai = np.full((SMALL_LAT.size, SMALL_LON.size), -0.001)
    r = np.argmin(np.abs(SMALL_LAT - 13.1))
    c = np.argmin(np.abs(SMALL_LON - -59.6))
    afai[r, c] = 0.003
    image, bounds = grid.to_mercator_rows(make_frame(afai=afai))

    rows, cols = np.nonzero(image == 0.003)
    y_top, y_bottom = merc(bounds.north), merc(bounds.south)
    step = (y_top - y_bottom) / image.shape[0]
    cell_south, cell_north = SMALL_LAT[r] - 0.25, SMALL_LAT[r] + 0.25  # 12.75 to 13.25 N
    for row in rows:
        # Each marked row's centre falls inside the marked data cell. (Its
        # edges may stick out by up to half a row: nearest-row copying.)
        centre = inverse_merc(y_top - (row + 0.5) * step)
        assert cell_south <= centre <= cell_north
    # Together, the marked rows cover Barbados's latitude, give or take half an
    # image row (the most nearest-row copying can shift anything).
    span_north = inverse_merc(y_top - rows.min() * step)
    span_south = inverse_merc(y_top - (rows.max() + 1) * step)
    half_row = (span_north - span_south) / len(rows) / 2
    assert span_south - half_row <= 13.1 <= span_north + half_row
    col_west = bounds.west + cols[0] * (bounds.east - bounds.west) / image.shape[1]
    assert col_west <= -59.6 < col_west + 1.0


def test_no_data_stays_no_data():
    afai = np.full((SMALL_LAT.size, SMALL_LON.size), np.nan)
    afai[10, 10] = 0.001
    image, _ = grid.to_mercator_rows(make_frame(afai=afai))
    assert np.isnan(image).sum() + (image == 0.001).sum() == image.size
