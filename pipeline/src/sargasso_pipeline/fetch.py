"""Download the newest 7-day AFAI frame from ERDDAP.

Polite by design (CLAUDE.md): one request at a time, a User-Agent naming the
project, retries that wait longer each time, and the mirror only as a fallback.
"""

import http.client
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import sources

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # how ERDDAP writes times, e.g. 2026-11-25T12:00:00Z


class FetchError(RuntimeError):
    """A download failed after all retries, or the server sent something unexpected."""


def http_get(url, attempts=4, timeout=180, sleep=time.sleep):
    """GET a URL and return the body as bytes. Retries after 2, 4 and 8 seconds."""
    request = urllib.request.Request(url, headers={"User-Agent": sources.USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as err:
            # A 4xx error means the request itself is wrong (except 429, "too
            # many requests"), so asking again won't help.
            if 400 <= err.code < 500 and err.code != 429:
                raise FetchError(f"HTTP {err.code} for {url}") from err
            problem = f"HTTP {err.code}"
        except (urllib.error.URLError, http.client.HTTPException, OSError) as err:
            problem = str(err) or type(err).__name__
        if attempt == attempts:
            raise FetchError(f"{problem} for {url} (gave up after {attempts} tries)")
        wait = 2**attempt
        print(f"  {problem}; trying again in {wait} s")
        sleep(wait)
    raise AssertionError("unreachable")


def griddap_url(server, file_type, query):
    """Build an ERDDAP griddap URL. Brackets and parentheses are percent-encoded."""
    encoded = urllib.parse.quote(query, safe="=,:")
    return f"{server['base_url']}/griddap/{server['dataset_7d']}.{file_type}?{encoded}"


def latest_time(server, get=http_get):
    """Ask a server for the time of its newest frame, as a UTC datetime."""
    text = get(griddap_url(server, "csv", "time[last]")).decode("utf-8", errors="replace")
    # ERDDAP's CSV has a header line ("time"), a units line ("UTC"), then the value.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    try:
        when = datetime.strptime(lines[-1], TIME_FORMAT)
    except (IndexError, ValueError) as err:
        raise FetchError(f"Unexpected reply to time[last] from {server['base_url']}") from err
    return when.replace(tzinfo=timezone.utc)


def frame_query(when, stride):
    """The ERDDAP query for one full-region frame, every `stride`-th cell."""
    t = when.strftime(TIME_FORMAT)
    s = sources
    return (
        f"{s.VARIABLE}[({t})]"
        f"[({s.LAT_MIN}):{stride}:({s.LAT_MAX})]"
        f"[({s.LON_MIN}):{stride}:({s.LON_MAX})]"
    )


def download_frame(server, when, stride, cache_dir=None, get=http_get):
    """Download one frame as NetCDF bytes. With cache_dir, reuse earlier downloads."""
    cache_file = None
    if cache_dir is not None:
        name = f"{server['dataset_7d']}_{when:%Y-%m-%d}_s{stride}.nc"
        cache_file = Path(cache_dir) / name
        if cache_file.exists():
            print(f"  using cached {cache_file}")
            return cache_file.read_bytes()
    data = get(griddap_url(server, "nc", frame_query(when, stride)))
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(data)
    return data


def fetch_newest(known_time=None, stride=sources.DAILY_STRIDE, cache_dir=None, get=None):
    """Try each server in order and return (server, time, netcdf_bytes).

    Returns None if the newest frame is not newer than `known_time`. Raises
    FetchError if every server fails, so the job stops loudly and the files
    already on the site stay as they are. Tests pass a fake `get`.
    """
    get = get or http_get
    failures = []
    for server in sources.SERVERS:
        print(f"Asking {server['base_url']} for its newest 7-day frame")
        try:
            when = latest_time(server, get=get)
            print(f"  newest frame: {when:{TIME_FORMAT}}")
            if known_time is not None and when <= known_time:
                return None
            data = download_frame(server, when, stride, cache_dir=cache_dir, get=get)
            print(f"  downloaded {len(data):,} bytes")
            return server, when, data
        except FetchError as err:
            print(f"  failed: {err}")
            failures.append(str(err))
    raise FetchError("Every server failed:\n  " + "\n  ".join(failures))
