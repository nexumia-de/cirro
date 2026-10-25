"""Polling and downloads against a local server that serves tars built
from the recorded RV member, and the refresh policy."""
import io
import tarfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from cirro import USER_AGENT, source

SAMPLE = Path(__file__).parent / "data" / "composite_rv_20261024_2110_000-hd5"
T0 = datetime(2026, 10, 24, 21, 10, tzinfo=timezone.utc)
TAR_NAME = "composite_rv_20261024_2110.tar"
ETAG = '"6addeee5-b1d000"'


def _tar():
    buffer = io.BytesIO()
    member = SAMPLE.read_bytes()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for lead in ("000", "005"):
            info = tarfile.TarInfo(f"composite_rv_20261024_2110_{lead}-hd5")
            info.size = len(member)
            tar.addfile(info, io.BytesIO(member))
    return buffer.getvalue()


@pytest.fixture
def server(request):
    body = _tar()
    files = {"/" + source.LATEST: body, "/" + TAR_NAME: body}
    log = []
    ranges = getattr(request, "param", True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            log.append((self.path, self.headers.get("Range"),
                        self.headers.get("User-Agent")))
            data = files.get(self.path)
            if data is None:
                self.send_error(404)
                return
            if self.headers.get("If-None-Match") == ETAG:
                self.send_response(304)
                self.end_headers()
                return
            header = self.headers.get("Range")
            if ranges and header:
                first, last = map(int, header.removeprefix("bytes=").split("-"))
                data = data[first:last + 1]
                self.send_response(206)
            else:
                self.send_response(200)
            self.send_header("ETag", ETAG)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/", log
    httpd.shutdown()


def test_stamp_roundtrip():
    assert source.stamp(T0) == "20261024_2110"
    assert source.parse_stamp("20261024_2110") == T0


@pytest.mark.parametrize("server", [True, False], indirect=True,
                         ids=["ranges", "no-ranges"])
def test_poll_latest(server):
    base_url, log = server
    latest = source.poll_latest(base_url=base_url)
    assert latest == source.Latest(T0, ETAG)
    assert log[0][:2] == ("/" + source.LATEST, "bytes=0-511")
    # Unchanged ETag: 304, nothing to do.
    assert source.poll_latest(ETAG, base_url) is None
    assert all(agent == USER_AGENT for _, _, agent in log)


@pytest.mark.parametrize("server", [True, False], indirect=True,
                         ids=["ranges", "no-ranges"])
def test_fetch_analysis(server):
    base_url, log = server
    name, data = source.fetch_analysis(T0, base_url)
    assert name == "composite_rv_20261024_2110_000-hd5"
    assert data == SAMPLE.read_bytes()
    assert [path for path, _, _ in log] == ["/" + TAR_NAME] * 2
    assert log[1][1] == f"bytes=512-{511 + len(data)}"


def test_fetch_tar(server):
    base_url, log = server
    members = source.fetch_tar(T0, base_url)
    assert [name for name, _ in members] == [
        "composite_rv_20261024_2110_000-hd5", "composite_rv_20261024_2110_005-hd5"]
    assert all(data == SAMPLE.read_bytes() for _, data in members)
    assert log == [("/" + TAR_NAME, None, USER_AGENT)]


def test_fetch_missing_analysis(server):
    base_url, _ = server
    with pytest.raises(source.urllib.error.HTTPError) as error:
        source.fetch_analysis(T0 - timedelta(minutes=5), base_url)
    assert error.value.code == 404


@pytest.mark.parametrize("minutes_after_t0, expected", [
    (4, 5),      # just fetched: next analysis appears at t0 + 9 min
    (7, 2),
    (8.5, 1),    # due within a minute: retry every minute
    (12, 1),     # late: keep retrying every minute …
    (20, 5),     # … for 10 minutes, then every 5 minutes
])
def test_next_poll(minutes_after_t0, expected):
    now = T0 + timedelta(minutes=minutes_after_t0)
    delay = source.next_poll(T0, now)
    assert delay == pytest.approx(timedelta(minutes=expected), abs=timedelta(seconds=31))


def test_next_poll_without_data():
    assert source.next_poll(None, T0) == source.POLL


def test_stale_guard():
    assert not source.is_stale(T0, T0 + timedelta(minutes=30))
    assert source.is_stale(T0, T0 + timedelta(minutes=31))
    assert source.is_stale(None, T0)
