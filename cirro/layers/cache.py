"""Disk cache of layer images (PNG), keyed by the request.

The GeoServer sends no `ETag` or `Cache-Control`, so Cirro decides:
images of a time step and model run don't change and are kept on disk
up to a size limit, oldest first out. Timeless layers (warnings) are
not cached here, they change at any moment. Thread safe."""
import hashlib
import logging
import os
import threading
from pathlib import Path

from gi.repository import GLib

log = logging.getLogger(__name__)

LIMIT = 80 * 1024 * 1024
DIRECTORY = Path(GLib.get_user_cache_dir()) / "cirro" / "layers"


def key(url):
    return hashlib.sha1(url.encode()).hexdigest()


class ImageCache:
    def __init__(self, directory=DIRECTORY, limit=LIMIT):
        self._dir = Path(directory)
        self._limit = limit
        self._lock = threading.Lock()
        self._size = None

    def _path(self, url):
        name = key(url)
        return self._dir / name[:2] / f"{name}.png"

    def get(self, url):
        path = self._path(url)
        try:
            data = path.read_bytes()
        except OSError:
            return None
        try:
            os.utime(path)   # most recently used
        except OSError:
            pass
        return data

    def put(self, url, data):
        path = self._path(url)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except OSError as error:
            log.warning("cannot cache %s: %s", path, error)
            return
        with self._lock:
            if self._size is None:
                self._size = self._measure()
            else:
                self._size += len(data)
            if self._size > self._limit:
                self._prune()

    def _files(self):
        return [p for p in self._dir.glob("*/*.png") if p.is_file()]

    def _measure(self):
        return sum(p.stat().st_size for p in self._files())

    def _prune(self):
        files = sorted(self._files(), key=lambda p: p.stat().st_mtime)
        size = sum(p.stat().st_size for p in files)
        # Down to 80 % so that pruning does not run on every write.
        while files and size > self._limit * 0.8:
            path = files.pop(0)
            try:
                size -= path.stat().st_size
                path.unlink()
            except OSError:
                pass
        self._size = size
