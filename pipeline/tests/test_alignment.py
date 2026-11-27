"""The committed frame lines up with the land layer the map draws on top of it.

The data has no values over land, so if the frame sits in the right place,
pixels that are entirely land on the map should all be "no data" (0). A frame
shifted by even a few pixels would put real values on land. This checks the
frame in public/data/ (each day's, when the daily job runs its tests).
"""

import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from sargasso_pipeline import REPO_ROOT, encode
from sargasso_pipeline.grid import mercator_y

DATA = REPO_ROOT / "public" / "data"
SUPERSAMPLE = 4  # draw land at 4x, then average, to find pixels that are fully land


def land_coverage(latest, land):
    """Share of each PNG pixel covered by land (0 to 1), drawn in the PNG's own grid."""
    width, height = latest["width"], latest["height"]
    b = latest["bounds"]
    top, bottom = mercator_y(b["north"]), mercator_y(b["south"])
    s = SUPERSAMPLE

    def to_pixels(ring):
        ring = np.asarray(ring, dtype=float)
        x = (ring[:, 0] - b["west"]) / (b["east"] - b["west"]) * width * s
        y = (top - mercator_y(ring[:, 1])) / (top - bottom) * height * s
        return list(zip(x.tolist(), y.tolist()))

    canvas = Image.new("L", (width * s, height * s), 0)
    draw = ImageDraw.Draw(canvas)
    geometries = land.get("geometries") or [f["geometry"] for f in land.get("features", [])]
    for geometry in geometries:
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        for rings in polygons:
            draw.polygon(to_pixels(rings[0]), fill=255)  # outline of the land
            for hole in rings[1:]:
                draw.polygon(to_pixels(hole), fill=0)  # lakes and other holes
    big = np.asarray(canvas, dtype=float) / 255
    return big.reshape(height, s, width, s).mean(axis=(1, 3))


@pytest.fixture(scope="module")
def frame_and_land():
    if not (DATA / "latest.json").exists():
        pytest.skip("No committed frame yet")
    latest = json.loads((DATA / "latest.json").read_text())
    codes = encode.load_png(DATA / latest["image"])
    land = json.loads((DATA / "land.geojson").read_text())
    return codes, land_coverage(latest, land)


def data_on_land(codes, fully_land, dx=0, dy=0):
    """How many fully-land pixels hold data, with the frame shifted by (dx, dy) pixels."""
    shifted = np.roll(codes, (dy, dx), axis=(0, 1))
    return int(((shifted != encode.NODATA) & fully_land).sum())


def test_fully_land_pixels_have_no_data(frame_and_land):
    codes, coverage = frame_and_land
    fully_land = coverage == 1.0
    assert fully_land.sum() > 10_000  # sanity: plenty of land in the frame
    # A few "land" pixels do hold data, and correctly so: Natural Earth's land
    # layer doesn't cut out lakes, but USF's data covers large lakes and
    # reservoirs (Okeechobee, Pontchartrain, Kentucky Lake, Izabal, Guri,
    # Brokopondo). That was 249 of 152,651 land pixels (0.16%) on 2026-11-26.
    # Allow up to 0.5%; a misplaced frame gives far more (see the next test).
    assert data_on_land(codes, fully_land) <= 0.005 * fully_land.sum()


def test_shifting_the_frame_puts_data_on_land(frame_and_land):
    # Proves the check above can catch a misplaced frame: any shift of 3
    # pixels (about 20 km) puts clearly more data on land.
    codes, coverage = frame_and_land
    fully_land = coverage == 1.0
    aligned = data_on_land(codes, fully_land)
    for dx, dy in [(3, 0), (-3, 0), (0, 3), (0, -3)]:
        assert data_on_land(codes, fully_land, dx, dy) > 3 * aligned + 20
