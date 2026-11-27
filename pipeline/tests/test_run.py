"""The whole daily update, end to end, with a fake network and synthetic data."""

import json
from datetime import datetime, timezone

import pytest

from conftest import netcdf_bytes
from sargasso_pipeline import encode, fetch, main, output, run, sources

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
    assert latest["levels"]["status"].startswith("pending")
    assert latest["encoding"]["nodata"] == 0
    assert latest["data_fraction"] == 1.0  # the synthetic frame has data everywhere
    assert latest["daily_frames"] == ["2026-11-25"]

    # The PNG exists and its size matches latest.json.
    codes = encode.load_png(data_dir / latest["image"])
    assert codes.shape == (latest["height"], latest["width"])

    # The corners are the outer edges of the synthetic grid's cells:
    # rows every 0.5 degrees from 0 to 38, columns every 1 degree from -98 to -38.
    assert latest["bounds"] == {"west": -98.5, "south": -0.25, "east": -37.5, "north": 38.25}


def test_frames_older_than_30_days_are_removed_and_not_listed(tmp_path, fake_get):
    data_dir = tmp_path / "data"
    (data_dir / "daily").mkdir(parents=True)
    (data_dir / "daily" / "2026-10-01.png").write_bytes(b"")  # 55 days before the new frame
    (data_dir / "daily" / "2026-11-20.png").write_bytes(b"")  # 5 days before
    run(data_dir, get=fake_get)

    latest = json.loads((data_dir / "latest.json").read_text())
    assert latest["daily_frames"] == ["2026-11-20", "2026-11-25"]
    assert not (data_dir / "daily" / "2026-10-01.png").exists()


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


def test_the_30_day_window_boundary(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    for name in ["2026-10-26", "2026-10-27", "2026-11-24"]:
        (daily / f"{name}.png").write_bytes(b"")
    newest = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    # Keeping 30 days means 2026-10-27 through 2026-11-25.
    assert [p.stem for p in output.frames_to_prune(daily, newest)] == ["2026-10-26"]


def test_a_corrupt_download_fails_loudly_and_changes_nothing(tmp_path, fake_get, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    run(data_dir, get=fake_get)
    before = (data_dir / "latest.json").read_text()

    def garbage(url):
        return TIME_CSV if "time%5Blast%5D" in url else b"<html>not a NetCDF file</html>"

    monkeypatch.setattr(fetch, "http_get", garbage)
    assert main(["--data-dir", str(data_dir), "--force"]) == 1
    assert "Couldn't read the downloaded NetCDF file" in capsys.readouterr().err
    assert (data_dir / "latest.json").read_text() == before
