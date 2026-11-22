"""Permission to run without a window and to start at login, from the
XDG background portal via libportal (docs/notifications.md)."""
import logging

import gi

gi.require_version("Xdp", "1.0")
gi.require_version("XdpGtk4", "1.0")
from gi.repository import GLib, Xdp, XdpGtk4  # noqa: E402

log = logging.getLogger(__name__)

REASON = "Notify about weather warnings and rain at your default place"
# Started at login without a window (cirro/main.py, --background).
COMMAND = ["cirro", "--background"]


def request(window, autostart, callback):
    """Ask the portal; `callback(allowed)` on the main thread. Outside a
    sandbox the portal allows it without asking."""
    try:
        portal = Xdp.Portal.initable_new()
    except GLib.Error as error:
        log.warning("background portal: %s", error.message)
        GLib.idle_add(callback, False)
        return
    parent = XdpGtk4.parent_new_gtk(window) if window else None
    flags = Xdp.BackgroundFlags.AUTOSTART if autostart else Xdp.BackgroundFlags.NONE

    def done(portal_, result):
        try:
            allowed = portal_.request_background_finish(result)
        except GLib.Error as error:
            log.warning("background portal: %s", error.message)
            allowed = False
        callback(allowed)

    portal.request_background(parent, REASON, COMMAND if autostart else None,
                              flags, None, done)
