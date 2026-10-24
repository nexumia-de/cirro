"""Range-request download of the analysis member, against a local server
that serves a tar built from the recorded RV member."""
import io
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from wetterblick import USER_AGENT, source

SAMPLE = Path(__file__).parent / "data" / "composite_rv_20261024_2110_000-hd5"
TAR_NAME = "composite_rv_20261024_2110.tar"


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
    ranges = request.param

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            log.append((self.path, self.headers.get("Range"),
                        self.headers.get("User-Agent")))
            data = files.get(self.path)
            if data is None:
                self.send_error(404)
                return
            header = self.headers.get("Range")
            if ranges and header:
                first, last = map(int, header.removeprefix("bytes=").split("-"))
                data = data[first:last + 1]
                self.send_response(206)
            else:
                self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/", log
    httpd.shutdown()


@pytest.mark.parametrize("server", [True, False], indirect=True,
                         ids=["ranges", "no-ranges"])
def test_fetch_analysis(server):
    base_url, log = server
    name, data = source.fetch_analysis(base_url)
    assert name == "composite_rv_20261024_2110_000-hd5"
    assert data == SAMPLE.read_bytes()
    # Header from LATEST, member from the immutable timestamped tar.
    assert [path for path, _, _ in log] == ["/" + source.LATEST, "/" + TAR_NAME]
    assert log[1][1] == f"bytes=512-{511 + len(data)}"
    assert all(agent == USER_AGENT for _, _, agent in log)
