"""The whole daily update, end to end, with a fake network and synthetic data."""

import json
from datetime import datetime, timezone

import pytest

from conftest import netcdf_bytes
from sargasso_pipeline import fetch, main, output, run, sources

TIME_CSV = b"time\nUTC\n2026-11-25T12:00:00Z\n"


@pytest.fixture
def fake_get(tmp_path):
    frame = netcdf_bytes(tmp_path)

    def get(url):
        return TIME_CSV if "time%5Blast%5D" in url else frame

    return get


def test_first_run_writes_the_png_and_latest_json(tmp_path, fake_get):
    data_dir = tmp_path / "data"
    assert run(data_dir, get=fake_get) == "updated"

    latest = json.loads((data_dir / "latest.json").read_text())
    assert latest["data_date"] == "2026-11-25"
    assert latest["dataset_id"] == sources.SERVERS[0]["dataset_7d"]
    assert (data_dir / latest["image"]).exists()
    assert latest["levels"]["status"].startswith("pending")
    assert latest["encoding"]["nodata"] == 0
    assert set(latest["bounds"]) == {"west", "south", "east", "north"}
    assert latest["daily_frames"] == ["2026-11-25"]


def test_second_run_with_no_new_frame_changes_nothing(tmp_path, fake_get):
    data_dir = tmp_path / "data"
    run(data_dir, get=fake_get)
    before = (data_dir / "latest.json").read_text()
    assert run(data_dir, get=fake_get) == "up to date"
    assert (data_dir / "latest.json").read_text() == before


def test_when_every_server_fails_the_last_good_frame_stays(tmp_path, fake_get, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    run(data_dir, get=fake_get)
    before = (data_dir / "latest.json").read_text()

    def broken(url):
        raise fetch.FetchError("server down")

    monkeypatch.setattr(fetch, "http_get", broken)  # every request fails
    exit_code = main(["--data-dir", str(data_dir), "--force"])

    assert exit_code == 1
    assert "Every server failed" in capsys.readouterr().err
    assert (data_dir / "latest.json").read_text() == before
    assert (data_dir / "daily" / "2026-11-25.png").exists()


def test_daily_frames_older_than_30_days_are_removed(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    for name in ["2026-10-26", "2026-10-27", "2026-11-24"]:
        (daily / f"{name}.png").write_bytes(b"")
    newest = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    removed = output.prune_daily(daily, newest)
    # Keeping 30 days means 2026-10-27 through 2026-11-25.
    assert [p.stem for p in removed] == ["2026-10-26"]
    assert sorted(p.stem for p in daily.glob("*.png")) == ["2026-10-27", "2026-11-24"]
