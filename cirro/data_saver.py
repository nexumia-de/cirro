"""Save mobile data (issue #34): on a metered connection the radar is
polled every 15 min instead of every 5 and the warnings every 30 min
instead of 10, unless the user turned "Save Mobile Data" off in the
preferences. Reload always fetches at once (docs/radar-architecture.md,
bandwidth)."""
import logging

from gi.repository import Gio, GLib, GObject

from cirro.timebar import SETTINGS

log = logging.getLogger(__name__)


def load_enabled(path=SETTINGS):
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.NONE)
        return keyfile.get_boolean("network", "save-mobile-data")
    except GLib.Error:
        return True


def save_enabled(enabled, path=SETTINGS):
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.KEEP_COMMENTS)
    except GLib.Error:
        pass
    keyfile.set_boolean("network", "save-mobile-data", enabled)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        keyfile.save_to_file(str(path))
    except (OSError, GLib.Error) as error:
        log.warning("cannot save %s: %s", path, error)


class DataSaver(GObject.Object):
    """`saving` is true while the connection is metered and saving is
    enabled."""

    saving = GObject.Property(type=bool, default=False)

    def __init__(self, enabled=True, monitor=None):
        super().__init__()
        self._enabled = enabled
        self._monitor = monitor or Gio.NetworkMonitor.get_default()
        self._monitor.connect("notify::network-metered", lambda *_: self._update())
        self._update()

    @property
    def enabled(self):
        return self._enabled

    def set_enabled(self, enabled):
        self._enabled = enabled
        self._update()

    def _update(self):
        saving = self._enabled and self._monitor.get_network_metered()
        if saving != self.saving:
            log.debug("save mobile data: %s", saving)
            self.saving = saving
