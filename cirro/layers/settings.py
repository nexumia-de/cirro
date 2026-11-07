"""The chosen map layers, kept in settings.ini next to the playback
speed: the base layer with its variant and the overlays with theirs."""
import logging

from gi.repository import GLib

from cirro.layers import catalogue
from cirro.timebar import SETTINGS

log = logging.getLogger(__name__)


def load(path=SETTINGS):
    """(base id, base variant, {overlay id: variant})."""
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.NONE)
    except GLib.Error:
        return catalogue.RADAR, 0, {}

    def read(name, default):
        try:
            return keyfile.get_string("layers", name)
        except GLib.Error:
            return default

    base = read("base", catalogue.RADAR)
    layer = catalogue.get(base)
    if base != catalogue.RADAR and (layer is None or layer.role != catalogue.BASE):
        base = catalogue.RADAR
    try:
        variant = int(read("base-variant", "0"))
    except ValueError:
        variant = 0
    overlays = {}
    for item in read("overlays", "").split(";"):
        name, _, number = item.partition(":")
        layer = catalogue.get(name)
        if layer is None or layer.role != catalogue.OVERLAY:
            continue
        try:
            overlays[name] = int(number or 0)
        except ValueError:
            overlays[name] = 0
    return base, variant, overlays


def save(base, variant, overlays, path=SETTINGS):
    keyfile = GLib.KeyFile()
    try:
        keyfile.load_from_file(str(path), GLib.KeyFileFlags.KEEP_COMMENTS)
    except GLib.Error:
        pass
    keyfile.set_string("layers", "base", base)
    keyfile.set_string("layers", "base-variant", str(variant))
    keyfile.set_string("layers", "overlays",
                       ";".join(f"{k}:{v}" for k, v in overlays.items()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        keyfile.save_to_file(str(path))
    except (OSError, GLib.Error) as error:
        log.warning("cannot save %s: %s", path, error)
