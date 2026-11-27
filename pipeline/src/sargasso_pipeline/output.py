"""Write the map's data files under public/data/.

Files are written to a temporary name first and then renamed, so the site
never sees a half-written file. latest.json is written last, only after the
new PNG is safely in place.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import encode, levels, sources

KEEP_DAYS = 30  # rolling window of daily frames


def read_latest(data_dir):
    """The current latest.json as a dict, or None if there isn't one yet."""
    path = Path(data_dir) / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def latest_time(data_dir):
    """Time of the frame the site shows now, or None."""
    latest = read_latest(data_dir)
    if not latest:
        return None
    return datetime.strptime(latest["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _replace_atomically(path, write):
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


def write_outputs(data_dir, server, when, codes, bounds):
    """Save the daily PNG, update latest.json and drop frames older than KEEP_DAYS.

    Returns the dict written to latest.json.
    """
    data_dir = Path(data_dir)
    daily_dir = data_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    date = when.strftime("%Y-%m-%d")
    png_path = daily_dir / f"{date}.png"
    _replace_atomically(png_path, lambda tmp: encode.save_png(codes, tmp))

    height, width = codes.shape
    latest = {
        "data_date": date,
        "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "composite": "7-day composite; ERDDAP's timestamp date (which days it covers is unverified)",
        "dataset_id": server["dataset_7d"],
        "server": server["base_url"],
        "variable": sources.VARIABLE,
        "index": "relative sargassum index derived from AFAI (not tons, not a forecast)",
        "image": f"daily/{date}.png",
        "width": width,
        "height": height,
        "bounds": {
            "west": round(bounds.west, 6),
            "south": round(bounds.south, 6),
            "east": round(bounds.east, 6),
            "north": round(bounds.north, 6),
        },
        "rows": "evenly spaced in Web Mercator, north at the top",
        "encoding": {
            "nodata": encode.NODATA,
            "first_code": encode.FIRST_CODE,
            "last_code": encode.LAST_CODE,
            "afai_min": sources.AFAI_MIN,
            "afai_max": sources.AFAI_MAX,
        },
        "levels": levels.levels_metadata(),
        "daily_frames": [],
    }

    removed = prune_daily(daily_dir, newest=when)
    latest["daily_frames"] = sorted(p.stem for p in daily_dir.glob("*.png"))

    text = json.dumps(latest, indent=2) + "\n"
    _replace_atomically(data_dir / "latest.json", lambda tmp: tmp.write_text(text))
    for path in removed:
        print(f"  removed old frame {path.name}")
    return latest


def prune_daily(daily_dir, newest):
    """Delete daily PNGs more than KEEP_DAYS - 1 days older than `newest`."""
    oldest_kept = (newest - timedelta(days=KEEP_DAYS - 1)).strftime("%Y-%m-%d")
    removed = []
    for path in daily_dir.glob("*.png"):
        if path.stem < oldest_kept:  # YYYY-MM-DD strings sort like dates
            path.unlink()
            removed.append(path)
    return removed
