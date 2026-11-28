"""Daily update: fetch the newest 7-day AFAI frame and write the map's data files.

Run it with `uv run sargasso-pipeline` from the pipeline/ folder.
It exits with an error (and changes nothing) if every server fails, so the
GitHub Action fails loudly and the site keeps showing the last good frame.
"""

import argparse
import sys
from pathlib import Path

from . import encode, grid, monthly, output
from .fetch import FetchError, fetch_newest

# pipeline/src/sargasso_pipeline/__init__.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[3]


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="sargasso-pipeline", description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "public" / "data",
        help="where to write latest.json and daily/ (default: public/data)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="reuse downloads saved here (for development, e.g. .cache)",
    )
    parser.add_argument(
        "--monthly",
        metavar="FIRST:LAST",
        help="instead of the daily update, build monthly maps, e.g. 2016-06:2026-10 (one-off backfill)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=3.0,
        help="seconds to wait before each monthly download (default 3)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild the files even if the newest frame is already on the site",
    )
    return parser.parse_args(argv)


def read_checked_frame(netcdf_bytes, when):
    """Read a downloaded frame and make sure it's the one we asked for.

    Raises ValueError for a broken, empty or mismatched frame, which makes
    fetch_newest try the next server.
    """
    frame = grid.read_frame(netcdf_bytes)
    if frame.time != when:
        raise ValueError(f"Asked for the frame at {when}, got {frame.time}")
    return frame


def run(data_dir, cache_dir=None, force=False, get=None):
    """Do one update. Returns a short status string."""
    known = None if force else output.current_frame_time(data_dir)
    result = fetch_newest(known_time=known, cache_dir=cache_dir, get=get, parse=read_checked_frame)
    if result is None:
        print("Already up to date: the site shows the newest frame.")
        return "up to date"

    server, when, frame = result
    image, bounds = grid.to_mercator_rows(frame)
    codes = encode.encode(image)
    latest = output.write_outputs(data_dir, server, when, codes, bounds)

    png = Path(data_dir) / latest["image"]
    print(f"Wrote {png} ({png.stat().st_size:,} bytes, {latest['width']}x{latest['height']})")
    return "updated"


def update_monthly(data_dir):
    """Add last month's map if it's missing. A failure here must not block
    the daily map, so it's reported as a GitHub Actions warning (shown on the
    run's summary page) and tried again on the next run."""
    try:
        monthly.update(data_dir)
    except (FetchError, ValueError) as err:
        print(f"::warning title=Monthly map not updated::{err}")


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.monthly:
            first, sep, last = args.monthly.partition(":")
            if not sep:
                raise ValueError("--monthly needs FIRST:LAST, e.g. 2016-06:2026-10")
            monthly.backfill(args.data_dir, first, last, pause=args.pause, cache_dir=args.cache_dir)
        else:
            run(args.data_dir, cache_dir=args.cache_dir, force=args.force)
            update_monthly(args.data_dir)
    except (FetchError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        print("Nothing was changed; the site keeps the last good frame.", file=sys.stderr)
        return 1
    return 0
