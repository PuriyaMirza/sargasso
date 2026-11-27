"""The PNG encoding round trip."""

import numpy as np
import pytest

from sargasso_pipeline import encode
from sargasso_pipeline.sources import AFAI_MAX, AFAI_MIN


def test_round_trip_through_a_png_file_is_within_half_a_step(tmp_path):
    rng = np.random.default_rng(0)
    afai = rng.uniform(AFAI_MIN, AFAI_MAX, size=(50, 80))
    afai[rng.random(afai.shape) < 0.3] = np.nan  # 30% no data

    path = tmp_path / "frame.png"
    encode.save_png(encode.encode(afai), path)
    back = encode.decode(encode.load_png(path))

    assert np.array_equal(np.isnan(back), np.isnan(afai))
    has_data = ~np.isnan(afai)
    assert np.max(np.abs(back[has_data] - afai[has_data])) <= encode.STEP / 2 + 1e-12


def test_zero_means_no_data_only():
    afai = np.array([np.nan, AFAI_MIN, AFAI_MIN - 1, 0.0, AFAI_MAX, AFAI_MAX + 1])
    codes = encode.encode(afai)
    assert codes.tolist()[0] == 0
    assert (codes[1:] >= 1).all()


def test_out_of_range_values_clip_to_the_ends():
    codes = encode.encode(np.array([AFAI_MIN - 1, AFAI_MIN, AFAI_MAX, AFAI_MAX + 1]))
    assert codes.tolist() == [1, 1, 255, 255]


def test_code_for_matches_encode():
    assert encode.code_for(AFAI_MIN) == 1
    assert encode.code_for(AFAI_MAX) == 255
    assert encode.decode(np.array([encode.code_for(0.001)], dtype=np.uint8))[0] == pytest.approx(
        0.001, abs=encode.STEP / 2
    )


def test_png_is_8_bit_grayscale(tmp_path):
    from PIL import Image

    path = tmp_path / "frame.png"
    encode.save_png(encode.encode(np.zeros((4, 4))), path)
    with Image.open(path) as image:
        assert image.mode == "L"
