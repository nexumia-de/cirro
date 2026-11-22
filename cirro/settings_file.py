"""Boolean user settings in `settings.ini` (the key file of the playback
speed, cirro/timebar.py): save mobile data, notifications."""
import logging

from gi.repository import GLib

from cirro.timebar import SETTINGS

log = logging.getLogger(__name__)


def load_bool(group, key, default, path=SETTINGS):
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.NONE)
        return keyfile.get_boolean(group, key)
    except GLib.Error:
        return default


def save_bool(group, key, value, path=SETTINGS):
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.KEEP_COMMENTS)
    except GLib.Error:
        pass
    keyfile.set_boolean(group, key, value)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        keyfile.save_to_file(str(path))
    except (OSError, GLib.Error) as error:
        log.warning("cannot save %s: %s", path, error)
