"""Checks the default place for new warnings and rain starting soon and
sends notifications, while the app runs, with or without a window
(docs/notifications.md). Rain every 15 min (30 when saving mobile data),
warnings when the shared CAP source changes."""
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gi.repository import Gio, GLib, GObject

from cirro.notify import alerts, rain
from cirro.places import PlaceStore
from cirro.warnings import cap

log = logging.getLogger(__name__)

RAIN_EVERY = timedelta(minutes=15)
RAIN_EVERY_METERED = timedelta(minutes=30)
STATE = Path(GLib.get_user_cache_dir()) / "cirro" / "notified.json"


def load_state(path=STATE):
    try:
        data = json.loads(path.read_text())
        return alerts.State(set(data.get("warnings", [])),
                            bool(data.get("raining_soon", False)))
    except (OSError, ValueError):
        return alerts.State()


def save_state(state, path=STATE):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Only identifiers still worth remembering: the last 500.
        warnings = sorted(state.warnings)[-500:]
        path.write_text(json.dumps({"warnings": warnings,
                                    "raining_soon": state.raining_soon}))
    except OSError as error:
        log.warning("cannot save %s: %s", path, error)


class Watcher(GObject.Object):
    def __init__(self, app, warnings, data_saver, places=None):
        """`warnings`: the application's WarningSource; `places()` returns
        the place store, read from disk on every check by default, so the
        window's changes count."""
        super().__init__()
        self._app = app
        self._places = places or (lambda: PlaceStore(read_only=True))
        self._warnings = warnings
        self._saver = data_saver
        self._state = load_state()
        self._running = False
        self._timer = 0
        self._checking = False
        warnings.connect("changed", lambda *_: self._check_warnings())

    @property
    def running(self):
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._warnings.hold("notify", True)
        self._check_warnings()
        self._check_rain()

    def stop(self):
        self._running = False
        self._warnings.hold("notify", False)
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0

    def _place(self):
        """(name, latitude, longitude) of the default place, or None."""
        store = self._places()
        place = store.default
        if not place.has_position:
            place = store.own
        if not place.has_position:
            return None
        return place.title, place.latitude, place.longitude

    def _send(self, key, title, body):
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        notification.set_default_action("app.activate")
        self._app.send_notification(key, notification)

    def _check_warnings(self):
        place = self._place()
        if not self._running or place is None:
            return
        name, latitude, longitude = place
        found = cap.at_point(self._warnings.warnings, latitude, longitude,
                             datetime.now(timezone.utc))
        for warning in alerts.new_warnings(found, self._state):
            title, body = alerts.warning_text(warning, name)
            self._send(f"warning-{warning.identifier}", title, body)
        save_state(self._state)

    def _check_rain(self):
        self._timer = 0
        if not self._running:
            return GLib.SOURCE_REMOVE
        place = self._place()
        if place is not None and not self._checking:
            self._checking = True
            name, latitude, longitude = place

            def work():
                try:
                    series = rain.fetch_series(latitude, longitude)
                except Exception as error:   # network, server
                    log.warning("rain check: %s", error)
                    series = None
                GLib.idle_add(self._rain_checked, name, series)
            threading.Thread(target=work, name="rain-check", daemon=True).start()
        every = RAIN_EVERY_METERED if self._saver.saving else RAIN_EVERY
        self._timer = GLib.timeout_add_seconds(int(every.total_seconds()),
                                               self._check_rain)
        return GLib.SOURCE_REMOVE

    def _rain_checked(self, name, series):
        self._checking = False
        if series:
            now = datetime.now(timezone.utc)
            minutes = rain.starts_in(series, now)
            dry = all(rate < rain.RAIN for _, rate in series)
            if alerts.rain_due(minutes, dry, self._state):
                title, body = alerts.rain_text(minutes, name)
                self._send("rain", title, body)
            save_state(self._state)
        return GLib.SOURCE_REMOVE
