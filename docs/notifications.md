---
type: Concept
title: Notifications
description: Opt-in local notifications for new warnings (level 2 and up) and rain starting within 30 min at the default place, also with the window closed, through the background portal; cheap checks from the CAP file and one WMS point query.
tags: [notifications, warnings, rain, background, battery]
generated: { by: claude-code/2.1.310, at: 2026-11-22T05:40:00Z }
sources:
  - "[^decision]: decisions/notifications.md"
  - "[^data]: data-sources.md, section 2"
---

# What the user sees

- Preferences → Places → **Notifications** (off by default). Turning it
  on asks the background portal for permission to run in the background
  and to start at login; if it refuses, the switch turns off again and a
  toast says why.
- For the default place (or the own location's last position when the
  default place has none):
  - "Frost warning, level 2" / "<place>: <DWD headline>" for every new
    warning of level 2 (Moderate) or higher. Updates of a warning that
    was notified are not notified again.
  - "Rain in about 20 min" / "At <place>" when it is dry now and rain
    (≥ 0.1 mm/h, the map's lowest class) starts within 30 min. One
    notification per shower: the next one only after the whole 2-hour
    series was dry.
- A tap on a notification opens the app.

# How it works

- `cirro/main.py`: the application owns the `WarningSource` and the
  `DataSaver`, shared with the window. With notifications on it holds
  itself, so closing the window leaves it running without the map, the
  radar frames or the window (≈ the size of the Python interpreter plus
  the CAP warnings). `cirro --background` (the portal's autostart
  command) starts without a window.
- `cirro/notify/background.py`: libportal `request_background` with
  `AUTOSTART`; turning notifications off asks again without autostart,
  which removes the login entry.
- `cirro/notify/watcher.py`: warnings are checked whenever the shared
  CAP source changes (it polls every 10 min, 30 when saving mobile data;
  an unchanged file costs one `304`); rain every 15 min (30 when saving
  mobile data) with one `GetCapabilities` (3 KB gzipped) and one
  `GetFeatureInfo` over the 2-hour time range (≈ 5 KB) instead of the
  2–12 MB tar.[^data] The place store is read from disk on every check,
  so changes in the window count. Notified identifiers are kept in
  `~/.cache/cirro/notified.json`.
- `cirro/notify/rain.py`, `cirro/notify/alerts.py`: the decisions, no
  GTK, tested in `tests/test_notify.py` with the recorded point series
  `tests/data/wms/info-rv-series.json` and the recorded CAP status.

Why this design: [decision](decisions/notifications.md).[^decision]

# Battery

Per hour in the background: about 4 rain checks (≈ 32 KB) and 6 CAP
polls (mostly `304`), each a few ms of CPU in Python; no radar decode.
Not yet measured on the phone: [owner checks](owner-checks.md).
