"""Turn AFAI values into an 8-bit grayscale "data PNG" and back.

PNG value 0 means no data (cloud, land, missing). Values 1 to 255 are the AFAI
index scaled linearly between sources.AFAI_MIN and sources.AFAI_MAX. The
browser reads these numbers and colors them with a lookup table.
"""

import numpy as np
from PIL import Image

from .sources import AFAI_MAX, AFAI_MIN

NODATA = 0
FIRST_CODE, LAST_CODE = 1, 255
STEP = (AFAI_MAX - AFAI_MIN) / (LAST_CODE - FIRST_CODE)  # AFAI per PNG step


def encode(afai):
    """AFAI array (NaN = no data) to uint8 codes. Out-of-range values are clipped."""
    codes = np.full(afai.shape, NODATA, dtype=np.uint8)
    has_data = np.isfinite(afai)
    clipped = np.clip(afai[has_data], AFAI_MIN, AFAI_MAX)
    codes[has_data] = FIRST_CODE + np.rint((clipped - AFAI_MIN) / STEP).astype(np.uint8)
    return codes


def decode(codes):
    """uint8 codes back to AFAI values (NaN where the code is 0).

    The tests use this and load_png to check the round trip; the browser
    decodes the same way using the numbers in latest.json.
    """
    afai = AFAI_MIN + (codes.astype(np.float64) - FIRST_CODE) * STEP
    afai[codes == NODATA] = np.nan
    return afai


def code_for(afai_value):
    """The PNG code for one AFAI value, e.g. for class breaks in latest.json."""
    return int(encode(np.array([afai_value]))[0])


def save_png(codes, path):
    """Write codes as an 8-bit grayscale PNG, compressed as tightly as Pillow can."""
    Image.fromarray(codes).save(path, format="PNG", optimize=True)


def load_png(path):
    """Read a data PNG back into a uint8 array."""
    with Image.open(path) as image:
        return np.asarray(image.convert("L"))
