"""Class breaks, tested on synthetic values.

The breaks used here are made-up test fixtures, not real thresholds. The real
LEVEL_BREAKS stay None until a published USF method is confirmed.
"""

import numpy as np
import pytest

from sargasso_pipeline import encode, levels

TEST_BREAKS = (0.0, 0.001, 0.002)  # synthetic, for testing the mechanics only


def test_classify_puts_values_in_the_right_level():
    afai = np.array([-0.001, 0.0, 0.0005, 0.001, 0.0015, 0.002, 0.003, np.nan])
    assert levels.classify(afai, TEST_BREAKS).tolist() == [0, 1, 1, 2, 2, 3, 3, -1]


def test_breaks_must_be_three_increasing_values():
    with pytest.raises(ValueError):
        levels.check_breaks((0.0, 0.001))
    with pytest.raises(ValueError):
        levels.check_breaks((0.0, 0.002, 0.001))


def test_metadata_says_pending_until_breaks_are_set():
    meta = levels.levels_metadata(None)
    assert meta["breaks_afai"] is None and meta["status"].startswith("pending")


def test_metadata_gives_png_codes_for_the_breaks():
    meta = levels.levels_metadata(TEST_BREAKS)
    assert meta["breaks_code"] == [encode.code_for(b) for b in TEST_BREAKS]
    assert meta["names"] == ["none", "low", "moderate", "high"]
