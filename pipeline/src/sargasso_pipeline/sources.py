"""Where the data comes from. Facts checked in Phase 0; see docs/DECISIONS.md."""

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
