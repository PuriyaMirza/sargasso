from sargasso_pipeline import sources


def test_region_and_servers_follow_the_data_rules():
    # Latitude ascends from the equator; longitude is west, so negative.
    assert (sources.LAT_MIN, sources.LAT_MAX) == (0.0, 38.0)
    assert (sources.LON_MIN, sources.LON_MAX) == (-98.0, -38.0)

    # The main server comes first, the mirror second, each with the 7-day
    # dataset ID checked in Phase 0 (docs/DECISIONS.md).
    assert sources.SERVERS == [
        {
            "base_url": "https://cwcgom.aoml.noaa.gov/erddap",
            "dataset_7d": "noaa_aoml_atlantic_oceanwatch_AFAI_7D",
        },
        {
            "base_url": "https://upwell.pfeg.noaa.gov/erddap",
            "dataset_7d": "noaa_aoml_ae10_d11a_85ab",
        },
    ]
    assert sources.VARIABLE == "AFAI"

    # Our User-Agent names the project and the repo.
    assert "github.com/PuriyaMirza/sargasso" in sources.USER_AGENT
