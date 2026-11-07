"""A line below the nowcast about the selected place: sunrise and
sunset (computed locally, issue #54) and the wind measured at the
nearest DWD station within 50 km (issue #59)."""
import logging
import threading
from datetime import datetime, timedelta, timezone

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

from cirro import sun, wind  # noqa: E402
from cirro.layers import wfs, wms  # noqa: E402
from cirro.timebar import clock  # noqa: E402

log = logging.getLogger(__name__)

WIND_LAYER, WIND_FIELD = "RBSN_FF", "SPEED"
WITHIN_KM = 50
# Measurements are hourly; look again this often.
REFRESH = timedelta(minutes=20)


def sun_text(latitude, longitude, day):
    rise, set_ = sun.sun_times(latitude, longitude, day)
    if rise == "day":
        return "No sunset today"
    if rise == "night":
        return "No sunrise today"
    return f"Sunrise {clock(rise)} · Sunset {clock(set_)}"


def wind_text(stations, latitude, longitude, measured):
    station, km = wfs.nearest(stations, latitude, longitude, WITHIN_KM)
    if station is None:
        return None
    where = f"{station.name}, {km:.0f} km" if km >= 1 else station.name
    return f"Wind {wind.describe(station.value, station.direction)} · {where} · {clock(measured)}"


def latest_wind():
    """(stations, measurement time) of the newest hour."""
    caps = wms.fetch_capabilities(WIND_LAYER)
    measured = caps.axis.last
    return wfs.fetch(WIND_LAYER, WIND_FIELD, measured), measured


class PlaceDetails(Gtk.Label):
    def __init__(self, live=True):
        """`live`: fetch the wind (not with recorded demo data)."""
        super().__init__(xalign=0, wrap=True, css_classes=["caption", "dim-label"],
                         visible=False)
        self._live = live
        self._position = None
        self._wind = None          # (stations, measured, fetched at)
        self._loading = False

    def set_place(self, position):
        self._position = position
        self._update()
        if self._live and position and not self._loading and (
                self._wind is None
                or datetime.now(timezone.utc) - self._wind[2] > REFRESH):
            self._load()

    def _load(self):
        self._loading = True

        def work():
            try:
                stations, measured = latest_wind()
                result = (stations, measured, datetime.now(timezone.utc))
            except Exception as error:   # network, server
                log.warning("wind: %s", error)
                result = None
            GLib.idle_add(self._loaded, result)
        threading.Thread(target=work, name="wind", daemon=True).start()

    def _loaded(self, result):
        self._loading = False
        if result is not None:
            self._wind = result
        self._update()
        return GLib.SOURCE_REMOVE

    def _update(self):
        if not self._position:
            self.set_visible(False)
            return
        latitude, longitude = self._position
        today = datetime.now().astimezone().date()
        lines = [sun_text(latitude, longitude, today)]
        if self._wind:
            text = wind_text(self._wind[0], latitude, longitude, self._wind[1])
            if text:
                lines.append(text)
        self.set_label("\n".join(lines))
        self.set_visible(True)
