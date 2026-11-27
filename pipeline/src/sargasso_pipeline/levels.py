"""Sargassum levels: none, low, moderate, high (plus no data).

The breaks between levels must come from USF's published method for turning
AFAI into sargassum coverage (docs/PLAN.md: no guessed thresholds). Phases 0
and 1 couldn't confirm that method from a primary source (docs/DECISIONS.md),
so LEVEL_BREAKS is None for now. Until it's set, the map shows the continuous
relative index, and latest.json says the levels are pending.
"""

import numpy as np

from .encode import code_for

LEVEL_NAMES = ("none", "low", "moderate", "high")
NO_DATA_LEVEL = -1

# Three AFAI values: the boundaries none|low, low|moderate and moderate|high.
# Set this only from a cited USF or NOAA source, and record it in DECISIONS.md.
LEVEL_BREAKS = None


def check_breaks(breaks):
    """Breaks must be three numbers in increasing order."""
    if len(breaks) != len(LEVEL_NAMES) - 1:
        raise ValueError(f"Need {len(LEVEL_NAMES) - 1} breaks, got {len(breaks)}")
    if not all(a < b for a, b in zip(breaks, breaks[1:])):
        raise ValueError(f"Breaks must increase: {breaks}")


def classify(afai, breaks):
    """Level index per pixel: 0 none, 1 low, 2 moderate, 3 high, -1 no data.

    A value equal to a break goes to the higher level.
    """
    check_breaks(breaks)
    levels = np.digitize(afai, breaks).astype(np.int8)
    levels[~np.isfinite(afai)] = NO_DATA_LEVEL
    return levels


def levels_metadata(breaks=LEVEL_BREAKS):
    """The `levels` block of latest.json, telling the browser how to color the PNG."""
    if breaks is None:
        return {
            "names": list(LEVEL_NAMES),
            "breaks_afai": None,
            "breaks_code": None,
            "status": "pending: no published method confirmed yet (see docs/DECISIONS.md)",
        }
    check_breaks(breaks)
    return {
        "names": list(LEVEL_NAMES),
        "breaks_afai": list(breaks),
        "breaks_code": [code_for(b) for b in breaks],
        "status": "set",
    }
