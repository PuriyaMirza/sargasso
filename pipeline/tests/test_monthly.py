"""Monthly maps: picking frames, averaging them, and the resumable backfill."""

import json
from datetime import datetime, timezone

import numpy as np
import pytest

from sargasso_pipeline import monthly, sources
from sargasso_pipeline.fetch import FetchError

from conftest import SMALL_LAT, SMALL_LON, netcdf_bytes


def utc(y, m, d):
    return datetime(y, m, d, 12, tzinfo=timezone.utc)


def test_months_between():
    assert monthly.months_between("2016-11", "2017-02") == ["2016-11", "2016-12", "2017-01", "2017-02"]
    assert monthly.months_between("2020-05", "2020-05") == ["2020-05"]
    with pytest.raises(ValueError):
        monthly.parse_month("2020-13")


def test_pick_weekly_takes_the_nearest_day_without_repeats():
    every_day = [utc(2025, 6, d) for d in range(1, 31)]
    assert [t.day for t in monthly.pick_weekly(every_day)] == [7, 14, 21, 28]
    # With gaps, the nearest available day is used, and a day is never used twice.
    gappy = [utc(2025, 6, d) for d in (2, 3, 16, 30)]
    assert [t.day for t in monthly.pick_weekly(gappy)] == [3, 16, 30]
    assert monthly.pick_weekly([]) == []


def test_composite_averages_and_keeps_no_data():
    a = np.array([[0.001, np.nan, np.nan]])
    b = np.array([[0.003, 0.002, np.nan]])
    out = monthly.composite([a, b])
    assert out[0, 0] == pytest.approx(0.002)
    assert out[0, 1] == pytest.approx(0.002)  # only one frame had data here
    assert np.isnan(out[0, 2])  # no data in any frame stays no data


class FakeServer:
    """Answers ERDDAP time-list and frame requests from canned data."""

    def __init__(self, tmp_path, days_by_month, fail=False):
        self.tmp_path = tmp_path
        self.days_by_month = days_by_month
        self.fail = fail
        self.requests = []

    def __call__(self, url):
        self.requests.append(url)
        if self.fail:
            raise FetchError(f"HTTP 503 for {url} (gave up after 4 tries)")
        if ".csv?" in url:
            month = next((m for m in self.days_by_month if f"{m}-01T00" in url), None)
            days = self.days_by_month.get(month, [])
            if not days:
                raise FetchError(f"HTTP 404 for {url}")
            y, mo = monthly.parse_month(month)
            lines = ["time", "UTC"] + [f"{y:04d}-{mo:02d}-{d:02d}T12:00:00Z" for d in days]
            return "\n".join(lines).encode()
        # A frame request: return a small frame for the requested date, with a
        # value that encodes the day so the average can be checked.
        stamp = url.split("AFAI%5B%28")[1][:10]
        when = datetime.strptime(stamp, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        afai = np.full((SMALL_LAT.size, SMALL_LON.size), when.day / 10000)
        afai[0, :] = np.nan  # a strip with no data
        return netcdf_bytes(self.tmp_path, afai=afai, when=when)


def test_backfill_writes_pngs_and_index_and_resumes(tmp_path, monkeypatch):
    server = FakeServer(tmp_path, {"2025-05": [7, 14, 21, 28], "2025-06": [], "2025-07": [10, 20]})
    monkeypatch.setattr(sources, "SERVERS", sources.SERVERS[:1])  # main server only
    data_dir = tmp_path / "data"
    index = monthly.backfill(data_dir, "2025-05", "2025-07", get=server, pause=0, sleep=lambda s: None)

    months = [m["month"] for m in index["months"]]
    assert months == ["2025-05", "2025-07"]  # June had no frames and was skipped
    assert index["months"][0]["frames"] == ["2025-05-07", "2025-05-14", "2025-05-21", "2025-05-28"]
    assert (data_dir / "monthly" / "2025-05.png").exists()
    assert not (data_dir / "monthly" / "2025-06.png").exists()
    on_disk = json.loads((data_dir / "monthly.json").read_text())
    assert on_disk == index
    assert on_disk["stride"] == monthly.MONTHLY_STRIDE
    assert 0 < on_disk["months"][0]["data_fraction"] < 1  # the no-data strip counts

    # June is long past, so it's remembered as empty: a second run asks nothing.
    assert monthly.read_index(data_dir)["empty_months"] == ["2025-06"]
    server.requests.clear()
    monthly.backfill(data_dir, "2025-05", "2025-07", get=server, pause=0, sleep=lambda s: None)
    assert server.requests == []


def test_a_recent_empty_month_is_asked_about_again(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "SERVERS", sources.SERVERS[:1])
    data_dir = tmp_path / "data"
    server = FakeServer(tmp_path, {"2025-05": [7], "2025-06": []})
    now = datetime(2025, 7, 2, tzinfo=timezone.utc)  # June only just ended
    monthly.backfill(data_dir, "2025-05", "2025-06", get=server, pause=0, sleep=lambda s: None, now=now)
    assert "empty_months" not in monthly.read_index(data_dir)
    server.requests.clear()
    monthly.backfill(data_dir, "2025-05", "2025-06", get=server, pause=0, sleep=lambda s: None, now=now)
    assert len(server.requests) == 1 and "2025-06-01" in server.requests[0]


def test_backfill_fails_loudly_and_keeps_finished_months(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "SERVERS", sources.SERVERS[:1])
    data_dir = tmp_path / "data"
    good = FakeServer(tmp_path, {"2025-05": [7]})
    monthly.backfill(data_dir, "2025-05", "2025-05", get=good, pause=0, sleep=lambda s: None)
    broken = FakeServer(tmp_path, {}, fail=True)
    with pytest.raises(FetchError):
        monthly.backfill(data_dir, "2025-05", "2025-06", get=broken, pause=0, sleep=lambda s: None)
    assert [m["month"] for m in monthly.read_index(data_dir)["months"]] == ["2025-05"]


def test_months_ago():
    now = datetime(2026, 1, 15, tzinfo=timezone.utc)
    assert monthly.months_ago(1, now) == "2025-12"
    assert monthly.months_ago(2, now) == "2025-11"
    assert monthly.months_ago(0, now) == "2026-01"


def test_update_waits_for_the_backfill(tmp_path):
    def no_network(url):
        raise AssertionError("update() must not download before the backfill exists")
    assert monthly.update(tmp_path, get=no_network) is None


def test_update_adds_last_month_and_remembers_old_empty_months(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "SERVERS", sources.SERVERS[:1])
    monkeypatch.setattr(monthly, "FIRST_MONTH", "2016-06")
    data_dir = tmp_path / "data"
    server = FakeServer(tmp_path, {"2016-06": [21], "2016-07": [], "2016-08": [7], "2016-09": [14]})
    monthly.backfill(data_dir, "2016-06", "2016-06", get=server, pause=0, sleep=lambda s: None)

    now = datetime(2016, 10, 3, tzinfo=timezone.utc)  # last finished month: September
    index = monthly.update(data_dir, now=now, get=server, pause=0, sleep=lambda s: None)
    assert [m["month"] for m in index["months"]] == ["2016-06", "2016-08", "2016-09"]
    assert index["empty_months"] == ["2016-07"]  # before August: old enough to remember

    server.requests.clear()
    monthly.update(data_dir, now=now, get=server, pause=0, sleep=lambda s: None)
    assert server.requests == []  # nothing left to ask about
