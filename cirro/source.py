"""Downloads of the RV nowcast composite from DWD open data.

Polling uses a conditional range request on `composite_rv_LATEST.tar`:
the first tar header names the analysis, and `If-None-Match` answers
`304` while nothing changed. The analysis and its 24 forecasts then come
from the immutable timestamped tar; past analyses are the first member
of older tars, fetched with two range requests each
(docs/data-sources.md, section 1). No GTK, so it runs in worker threads.
"""
import io
import logging
import re
import tarfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cirro import USER_AGENT

BASE_URL = "https://opendata.dwd.de/weather/radar/composite/rv/"
LATEST = "composite_rv_LATEST.tar"
_MEMBER = re.compile(r"composite_rv_(\d{8}_\d{4})_000-hd5")
_STAMP = "%Y%m%d_%H%M"

log = logging.getLogger(__name__)
# Bytes received, for the bandwidth measurement (CIRRO_DEBUG=1).
_received = 0
_received_lock = threading.Lock()


def received_bytes():
    return _received


def stamp(time_):
    """UTC datetime → the `YYYYMMDD_HHMM` part of DWD file names."""
    return time_.astimezone(timezone.utc).strftime(_STAMP)


def parse_stamp(text):
    return datetime.strptime(text, _STAMP).replace(tzinfo=timezone.utc)


def tar_url(analysis_time, base_url=BASE_URL):
    return f"{base_url}composite_rv_{stamp(analysis_time)}.tar"


def _get(url, first=None, last=None, etag=None, timeout=30):
    """GET `url`, optionally a byte range. Returns (body, ETag), or None
    for `304 Not Modified`."""
    headers = {"User-Agent": USER_AGENT}
    if first is not None:
        headers["Range"] = f"bytes={first}-{last}"
    if etag:
        headers["If-None-Match"] = etag
    request = urllib.request.Request(url, headers=headers)
    started = time.monotonic()
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code == 304:
            log.debug("%s: 304", url)
            return None
        raise
    with response:
        body = response.read()
        status = response.status
        tag = response.headers.get("ETag")
    global _received
    with _received_lock:
        _received += len(body)
    log.debug("%s: %d, %d bytes in %.2f s", url, status, len(body),
              time.monotonic() - started)
    if first is not None and status != 206:
        # Server ignored the range: cut the requested part out ourselves.
        body = body[first:last + 1]
    return body, tag


def _header(data):
    return tarfile.TarInfo.frombuf(data, tarfile.ENCODING, "surrogateescape")


@dataclass(frozen=True)
class Latest:
    analysis_time: datetime
    etag: str | None


def poll_latest(etag=None, base_url=BASE_URL):
    """Analysis time of `composite_rv_LATEST.tar`, or None if its ETag is
    still `etag`. Costs one 512-byte range request."""
    result = _get(base_url + LATEST, 0, 511, etag=etag)
    if result is None:
        return None
    data, tag = result
    header = _header(data)
    match = _MEMBER.fullmatch(header.name)
    if not match:
        raise ValueError(f"unexpected first tar member {header.name!r}")
    return Latest(parse_stamp(match[1]), tag)


def fetch_tar(analysis_time, base_url=BASE_URL):
    """All members (name, HDF5 bytes) of the tar of one analysis: the
    analysis itself and its forecasts up to +120 min."""
    data, _ = _get(tar_url(analysis_time, base_url))
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        return [(member.name, tar.extractfile(member).read())
                for member in tar.getmembers() if member.isfile()]


def fetch_analysis(analysis_time, base_url=BASE_URL):
    """(member name, HDF5 bytes) of one analysis frame, without the
    forecasts: the first tar member, fetched with two range requests."""
    url = tar_url(analysis_time, base_url)
    data, _ = _get(url, 0, 511)
    header = _header(data)
    if header.name != f"composite_rv_{stamp(analysis_time)}_000-hd5":
        raise ValueError(f"unexpected first tar member {header.name!r}")
    data, _ = _get(url, 512, 511 + header.size)
    if len(data) != header.size:
        raise ValueError(f"short read: {len(data)} of {header.size} bytes")
    return header.name, data


# Refresh policy (docs/radar-architecture.md, RadarSource).
STEP = timedelta(minutes=5)
# A new analysis appears 3–4 min after its nominal time.
PUBLISH_DELAY = timedelta(minutes=4)
RETRY = timedelta(minutes=1)
# How long to retry every minute when a new analysis is late.
RETRY_FOR = timedelta(minutes=10)
POLL = timedelta(minutes=5)
# Older data is not shown as current (stale guard).
STALE_AFTER = timedelta(minutes=30)


def next_poll(analysis_time, now):
    """Delay until the next poll, given the newest analysis we have."""
    if analysis_time is None:
        return POLL
    due = analysis_time + STEP + PUBLISH_DELAY
    if due - now >= RETRY:
        return min(due - now, POLL)
    return RETRY if now - due < RETRY_FOR else POLL


def is_stale(analysis_time, now):
    return analysis_time is None or now - analysis_time > STALE_AFTER
