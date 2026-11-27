"""Downloads: retries, the mirror fallback and loud failure, with a fake network."""

import urllib.error
from datetime import datetime, timezone

import pytest

from sargasso_pipeline import fetch, sources

PRIMARY = sources.SERVERS[0]["base_url"]
MIRROR = sources.SERVERS[1]["base_url"]
TIME_CSV = b"time\nUTC\n2026-11-25T12:00:00Z\n"


class FakeNetwork:
    """Answers requests from a table; servers listed in `down` always fail."""

    def __init__(self, down=(), frame=b"NETCDF"):
        self.down = set(down)
        self.frame = frame
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        if any(url.startswith(host) for host in self.down):
            raise fetch.FetchError(f"down: {url}")
        return TIME_CSV if "time%5Blast%5D" in url else self.frame


def test_uses_the_main_server_when_it_works():
    net = FakeNetwork()
    server, when, data = fetch.fetch_newest(get=net)
    assert server["base_url"] == PRIMARY
    assert when == datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    assert data == b"NETCDF"
    assert all(url.startswith(PRIMARY) for url in net.urls)


def test_falls_back_to_the_mirror_with_its_own_dataset_id():
    net = FakeNetwork(down=[PRIMARY])
    server, _, _ = fetch.fetch_newest(get=net)
    assert server["base_url"] == MIRROR
    assert "noaa_aoml_ae10_d11a_85ab.nc" in net.urls[-1]


def test_fails_loudly_when_every_server_fails():
    with pytest.raises(fetch.FetchError, match="Every server failed"):
        fetch.fetch_newest(get=FakeNetwork(down=[PRIMARY, MIRROR]))


def test_skips_the_download_when_already_up_to_date():
    net = FakeNetwork()
    known = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    assert fetch.fetch_newest(known_time=known, get=net) is None
    assert len(net.urls) == 1  # only the tiny time[last] request


def test_frame_url_asks_for_the_whole_region_at_the_daily_stride():
    when = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    url = fetch.griddap_url(sources.SERVERS[0], "nc", fetch.frame_query(when, 4))
    assert url.startswith(PRIMARY + "/griddap/noaa_aoml_atlantic_oceanwatch_AFAI_7D.nc?AFAI")
    assert "%5B%282026-11-25T12:00:00Z%29%5D" in url
    assert "%5B%280.0%29:4:%2838.0%29%5D" in url
    assert "%5B%28-98.0%29:4:%28-38.0%29%5D" in url


def test_a_garbled_time_reply_is_an_error():
    with pytest.raises(fetch.FetchError, match="Unexpected reply"):
        fetch.latest_time(sources.SERVERS[0], get=lambda url: b"<html>maintenance</html>")


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_http_get_retries_with_growing_waits_and_sends_our_user_agent(monkeypatch):
    calls, waits = [], []

    def fake_urlopen(request, timeout):
        calls.append(request)
        if len(calls) < 3:
            raise urllib.error.URLError("connection reset")
        return FakeResponse(b"ok")

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    assert fetch.http_get("https://example.test/x", sleep=waits.append) == b"ok"
    assert waits == [2, 4]
    assert calls[0].get_header("User-agent") == sources.USER_AGENT


def test_http_get_does_not_retry_a_client_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    waits = []
    with pytest.raises(fetch.FetchError, match="HTTP 404"):
        fetch.http_get("https://example.test/x", sleep=waits.append)
    assert waits == []
