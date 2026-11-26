from sargasso_pipeline import sources


def test_region_and_servers_follow_the_data_rules():
    # Latitude ascends from the equator; longitude is west, so negative.
    assert sources.LAT_MIN == 0.0 and sources.LAT_MAX == 38.0
    assert sources.LON_MIN < sources.LON_MAX < 0

    # The main server comes first, the mirror second, both over HTTPS.
    hosts = [s["base_url"] for s in sources.SERVERS]
    assert hosts == [
        "https://cwcgom.aoml.noaa.gov/erddap",
        "https://upwell.pfeg.noaa.gov/erddap",
    ]

    # Our User-Agent names the project and the repo.
    assert "github.com/PuriyaMirza/sargasso" in sources.USER_AGENT
