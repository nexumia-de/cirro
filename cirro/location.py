"""Own location through the XDG location portal (GeoClue behind it), via
libportal. Works inside and outside the Flatpak; no extra permission."""
import logging

import gi

gi.require_version("Xdp", "1.0")
gi.require_version("XdpGtk4", "1.0")
from gi.repository import GLib, GObject, Xdp, XdpGtk4  # noqa: E402

log = logging.getLogger(__name__)

# Report moves of 200 m or more; finer steps do not matter on a 1 km grid.
DISTANCE_M = 200
# EXACT lets GeoClue use the phone's GNSS; the coarser levels rely on
# Wi-Fi and cell lookups that are often unavailable
# (docs/radar-architecture.md, own location).
ACCURACY = Xdp.LocationAccuracy.EXACT


class Location(GObject.Object):
    """`changed(latitude, longitude, accuracy in m)` on every fix;
    `failed(message)` if the portal or the user refuses."""

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (float, float, float)),
        "failed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        super().__init__()
        self._portal = None
        self._running = False
        self.fix = None            # (latitude, longitude, accuracy)

    @property
    def running(self):
        return self._running

    def start(self, window):
        if self._running:
            return
        try:
            if self._portal is None:
                self._portal = Xdp.Portal.initable_new()
                self._portal.connect("location-updated", self._on_updated)
        except GLib.Error as error:
            self._fail(error.message)
            return
        self._running = True
        self._portal.location_monitor_start(
            XdpGtk4.parent_new_gtk(window), DISTANCE_M, 0, ACCURACY,
            Xdp.LocationMonitorFlags.NONE, None, self._on_started)

    def stop(self):
        if self._running:
            self._portal.location_monitor_stop()
            self._running = False

    def _on_started(self, portal, result):
        try:
            if portal.location_monitor_start_finish(result):
                return
            message = "The location portal refused"
        except GLib.Error as error:
            message = error.message
        self._running = False
        self._fail(message)

    def _on_updated(self, portal, latitude, longitude, altitude, accuracy,
                    speed, heading, description, seconds, microseconds):
        self.fix = (latitude, longitude, accuracy)
        self.emit("changed", latitude, longitude, accuracy)

    def _fail(self, message):
        log.warning("location unavailable: %s", message)
        self.emit("failed", message)
