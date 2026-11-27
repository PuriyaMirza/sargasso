"""Write the map's data files under public/data/.

Order matters, so the site never points at a missing or half-written file:
1. the new PNG (written to a temporary name, then renamed),
2. latest.json (same trick), which now points at the new PNG,
3. only then, delete frames older than KEEP_DAYS.
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


def current_frame_time(data_dir):
    """Time of the frame the site shows now (from latest.json), or None."""
    latest = read_latest(data_dir)
    if not latest:
        return None
    return datetime.strptime(latest["time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _replace_atomically(path, write):
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


def write_outputs(data_dir, server, when, codes, bounds):
    """Save the daily PNG, update latest.json, then drop frames older than KEEP_DAYS.

    Returns the dict written to latest.json.
    """
    data_dir = Path(data_dir)
    daily_dir = data_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    # 1. The new PNG.
    date = when.strftime("%Y-%m-%d")
    _replace_atomically(daily_dir / f"{date}.png", lambda tmp: encode.save_png(codes, tmp))

    # 2. latest.json, listing the frames that will remain after step 3.
    too_old = frames_to_prune(daily_dir, newest=when)
    kept = sorted(p.stem for p in daily_dir.glob("*.png") if p not in too_old)
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
        "data_fraction": round(float((codes != encode.NODATA).mean()), 4),
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
        "daily_frames": kept,
    }
    text = json.dumps(latest, indent=2) + "\n"
    _replace_atomically(data_dir / "latest.json", lambda tmp: tmp.write_text(text))

    # 3. Old frames, now that nothing points at them.
    for path in too_old:
        path.unlink()
        print(f"  removed old frame {path.name}")
    return latest


def frames_to_prune(daily_dir, newest):
    """Daily PNGs more than KEEP_DAYS - 1 days older than `newest`."""
    oldest_kept = (newest - timedelta(days=KEEP_DAYS - 1)).strftime("%Y-%m-%d")
    # YYYY-MM-DD names sort like dates, so plain string comparison works.
    return sorted(p for p in daily_dir.glob("*.png") if p.stem < oldest_kept)
