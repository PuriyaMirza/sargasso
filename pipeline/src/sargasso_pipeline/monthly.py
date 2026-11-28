"""Monthly maps for the History view: one PNG per month since June 2016.

A month's map is the average, pixel by pixel, of that month's 7-day frames
nearest days 7, 14, 21 and 28 (up to four frames). A pixel with no data in
any of them stays no data. This is a picture of the month, not a measurement:
no thresholds or levels are applied (docs/DECISIONS.md).

Run the one-off backfill with
    uv run sargasso-pipeline --monthly 2016-06:2026-10
It is polite (one request at a time, a pause between requests) and can be
stopped and restarted: months already in monthly.json are skipped.
"""

import calendar
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import encode, grid, sources
from .fetch import TIME_FORMAT, FetchError, download_frame, griddap_url, http_get
from .output import _replace_atomically

MONTHLY_STRIDE = 6  # about 10 km per pixel (docs/PLAN.md)
TARGET_DAYS = (7, 14, 21, 28)  # roughly one 7-day frame per week of the month
FIRST_MONTH = "2016-06"  # the dataset starts on 2016-06-18


def parse_month(text):
    """'2016-06' -> (2016, 6). Raises ValueError for anything else."""
    year, month = datetime.strptime(text, "%Y-%m").timetuple()[:2]
    return year, month


def months_between(first, last):
    """Every 'YYYY-MM' from first to last, inclusive."""
    year, month = parse_month(first)
    end = parse_month(last)
    out = []
    while (year, month) <= end:
        out.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def month_times(server, month, get=http_get):
    """The frame times a server lists for a month, or [] if it has none."""
    year, mon = parse_month(month)
    last_day = calendar.monthrange(year, mon)[1]
    query = f"time[({year:04d}-{mon:02d}-01T00:00:00Z):1:({year:04d}-{mon:02d}-{last_day:02d}T23:59:59Z)]"
    try:
        text = get(griddap_url(server, "csv", query)).decode("utf-8", errors="replace")
    except FetchError as err:
        # ERDDAP answers 404 when no times fall in the range (the data has gaps).
        if "HTTP 404" in str(err):
            return []
        raise
    times = []
    for line in text.splitlines()[2:]:  # skip the "time" and "UTC" header lines
        line = line.strip()
        if line:
            times.append(datetime.strptime(line, TIME_FORMAT).replace(tzinfo=timezone.utc))
    return times


def pick_weekly(times):
    """For each target day, the available time nearest to it (no repeats), in order."""
    picked = []
    for day in TARGET_DAYS:
        if not times:
            break
        best = min(times, key=lambda t: (abs(t.day - day), t))
        if best not in picked:
            picked.append(best)
    return sorted(picked)


def composite(afai_stack):
    """Pixel-by-pixel mean of several frames, ignoring no-data (NaN) values.

    Pixels with no data in every frame stay NaN.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)  # "mean of empty slice"
        return np.nanmean(np.stack(afai_stack), axis=0)


def build_month(server, month, get=http_get, pause=3.0, sleep=time.sleep, cache_dir=None):
    """Download a month's weekly frames from one server and average them.

    Returns (frame, dates) where frame.afai is the composite, or None if the
    server has no frames in that month. Raises FetchError or ValueError if a
    download fails or a frame looks wrong.
    """
    times = month_times(server, month, get=get)
    picked = pick_weekly(times)
    if not picked:
        return None
    frames = []
    for when in picked:
        sleep(pause)  # be polite: a pause before every download
        data = download_frame(server, when, MONTHLY_STRIDE, cache_dir=cache_dir, get=get)
        frame = grid.read_frame(data)
        if frame.time != when:
            raise ValueError(f"Asked for the frame at {when}, got {frame.time}")
        if frames and (frame.lat.shape != frames[0].lat.shape or frame.lon.shape != frames[0].lon.shape):
            raise ValueError(f"The frame at {when} has a different grid from the others")
        frames.append(frame)
    first = frames[0]
    month_frame = grid.Frame(lat=first.lat, lon=first.lon, afai=composite([f.afai for f in frames]), time=first.time)
    return month_frame, [f"{t:%Y-%m-%d}" for t in picked]


def months_ago(n, now=None):
    """'YYYY-MM' for the month n months before the current UTC month."""
    now = now or datetime.now(timezone.utc)
    total = now.year * 12 + (now.month - 1) - n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def update(data_dir, now=None, get=None, pause=3.0, sleep=time.sleep):
    """Daily-job step: add any finished month missing from monthly.json.

    Does nothing until the one-off backfill has created monthly.json. The
    last finished month is the one before the current UTC month.
    """
    if read_index(data_dir) is None:
        print("No monthly.json yet; run the --monthly backfill first. Skipping monthly maps.")
        return None
    return backfill(data_dir, FIRST_MONTH, months_ago(1, now), get=get, pause=pause, sleep=sleep, now=now,
                    keep_going=True)


def read_index(data_dir):
    path = Path(data_dir) / "monthly.json"
    return json.loads(path.read_text()) if path.exists() else None


def write_index(data_dir, index):
    text = json.dumps(index, indent=2) + "\n"
    _replace_atomically(Path(data_dir) / "monthly.json", lambda tmp: tmp.write_text(text))


def new_index(bounds, codes):
    height, width = codes.shape
    return {
        "composite": "mean of the month's 7-day frames nearest days 7, 14, 21 and 28; "
        "no thresholds applied",
        "variable": sources.VARIABLE,
        "index": "relative sargassum index derived from AFAI (not tons, not a forecast)",
        "stride": MONTHLY_STRIDE,
        "width": width,
        "height": height,
        "bounds": {k: round(getattr(bounds, k), 6) for k in ("west", "south", "east", "north")},
        "rows": "evenly spaced in Web Mercator, north at the top",
        "encoding": {
            "nodata": encode.NODATA,
            "first_code": encode.FIRST_CODE,
            "last_code": encode.LAST_CODE,
            "afai_min": sources.AFAI_MIN,
            "afai_max": sources.AFAI_MAX,
        },
        "months": [],
    }


def _build_from_any_server(month, get, pause, sleep, cache_dir):
    """Try each server in turn. Returns (frame, dates), or None only if every
    server answered and none has frames for the month. Raises FetchError if
    no server had frames and at least one failed, so a temporary outage is
    never mistaken for an empty month."""
    failures = []
    for server in sources.SERVERS:
        print(f"{month}: asking {server['base_url']}")
        try:
            result = build_month(server, month, get=get, pause=pause, sleep=sleep, cache_dir=cache_dir)
        except (FetchError, ValueError) as err:
            print(f"  failed: {err}")
            failures.append(str(err))
            continue
        if result is not None:
            return result
        print("  no frames listed for this month")
    if failures:
        raise FetchError(f"{month}: no frames found, and a server failed:\n  " + "\n  ".join(failures))
    return None


def backfill(data_dir, first, last, get=None, pause=3.0, sleep=time.sleep, cache_dir=None, now=None,
             keep_going=False):
    """Build monthly/YYYY-MM.png for every month from first to last.

    Months already listed in monthly.json are skipped, so a stopped run can be
    restarted. The index is rewritten after each month. A month that no server
    has frames for is reported and skipped. If a month fails, this raises
    FetchError (leaving every finished month in place), unless keep_going is
    set, as in the daily job: then it warns and moves on to later months.
    """
    get = get or http_get
    data_dir = Path(data_dir)
    out_dir = data_dir / "monthly"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = read_index(data_dir)
    done = {m["month"] for m in index["months"]} if index else set()
    done |= set(index.get("empty_months", [])) if index else set()

    for month in months_between(first, last):
        if month in done:
            continue
        try:
            result = _build_from_any_server(month, get, pause, sleep, cache_dir)
        except (FetchError, ValueError) as err:
            if not keep_going:
                raise
            # The daily job: warn (shown on the run's summary page) and go on
            # to later months; this month is tried again next run.
            print(f"::warning title=Monthly map {month} not built::{err}")
            continue
        if result is None:
            print(f"  {month}: no server has frames in this month; skipped")
            # Remember long-past empty months (the data has gaps, e.g. late
            # 2016) so later runs don't ask again. Only when every server
            # answered "none"; a recent month might still be filling in.
            if index is not None and month < months_ago(2, now):
                index["empty_months"] = sorted(set(index.get("empty_months", [])) | {month})
                write_index(data_dir, index)
            continue

        frame, dates = result
        image, bounds = grid.to_mercator_rows(frame)
        codes = encode.encode(image)
        png = out_dir / f"{month}.png"
        _replace_atomically(png, lambda tmp: encode.save_png(codes, tmp))

        if index is None:
            index = new_index(bounds, codes)
        elif (index["height"], index["width"]) != codes.shape:
            raise ValueError(f"{month}: image size {codes.shape} differs from earlier months")
        index["months"].append({
            "month": month,
            "frames": dates,
            "data_fraction": round(float((codes != encode.NODATA).mean()), 4),
        })
        index["months"].sort(key=lambda m: m["month"])
        write_index(data_dir, index)
        print(f"  wrote {png.name} ({png.stat().st_size:,} bytes) from {len(dates)} frames: {', '.join(dates)}")
    return index
