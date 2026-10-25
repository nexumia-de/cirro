"""Download of the current RV analysis frame from DWD open data.

Only the `_000` member is needed for a static frame. It is the first
entry of every tar, so it is fetched with two range requests instead of
the whole 2–11 MB tar (docs/data-sources.md, section 1).
"""
import re
import tarfile
import urllib.request

from cirro import USER_AGENT

BASE_URL = "https://opendata.dwd.de/weather/radar/composite/rv/"
LATEST = "composite_rv_LATEST.tar"
_MEMBER = re.compile(r"composite_rv_(\d{8}_\d{4})_000-hd5")


def _get(url, first, last, timeout=30):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Range": f"bytes={first}-{last}",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.status == 206:
            return body
        # Server ignored the range: cut the requested part out ourselves.
        return body[first:last + 1]


def fetch_analysis(base_url=BASE_URL):
    """Return (member name, HDF5 bytes) of the newest analysis frame."""
    header = tarfile.TarInfo.frombuf(_get(base_url + LATEST, 0, 511),
                                     tarfile.ENCODING, "surrogateescape")
    match = _MEMBER.fullmatch(header.name)
    if not match:
        raise ValueError(f"unexpected first tar member {header.name!r}")
    # LATEST may be replaced between the two requests; the timestamped tar
    # named by the header does not change.
    tar_url = f"{base_url}composite_rv_{match[1]}.tar"
    data = _get(tar_url, 512, 511 + header.size)
    if len(data) != header.size:
        raise ValueError(f"short read: {len(data)} of {header.size} bytes")
    return header.name, data
