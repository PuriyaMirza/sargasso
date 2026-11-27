"""Where the data comes from and how we sample it. Facts checked in Phase 0;
see docs/DECISIONS.md."""

# Identify ourselves to NOAA's servers, as CLAUDE.md asks.
USER_AGENT = "sargasso-map/0.1 (+https://github.com/PuriyaMirza/sargasso)"

# Main server first, fallback mirror second. The two servers give the same
# 7-day dataset different IDs, so each server keeps its own.
SERVERS = [
    {
        "base_url": "https://cwcgom.aoml.noaa.gov/erddap",
        "dataset_7d": "noaa_aoml_atlantic_oceanwatch_AFAI_7D",
    },
    {
        "base_url": "https://upwell.pfeg.noaa.gov/erddap",
        "dataset_7d": "noaa_aoml_ae10_d11a_85ab",
    },
]

VARIABLE = "AFAI"

# Region covered by the data, in degrees. Latitude ascends (south to north);
# longitude is negative (west of Greenwich).
LAT_MIN, LAT_MAX = 0.0, 38.0
LON_MIN, LON_MAX = -98.0, -38.0

# Take every 4th grid cell in each direction for the daily map: about 6.7 km
# per pixel instead of 1.7 km. Every 3rd cell (5 km) made a 330 KB image, over
# the 300 KB storage gate in docs/PLAN.md; every 4th makes about 190 KB.
DAILY_STRIDE = 4

# The range of AFAI values the dataset reports (its `actual_range` attribute).
# The PNG encoding maps this range onto values 1..255; anything outside is
# clipped to the nearest end. This is the data's own range, not a threshold.
AFAI_MIN, AFAI_MAX = -0.002, 0.004
