---
type: Decision Record
title: Radar focus, no forecast view
description: Accepted - Cirro covers radar, rain nowcast, warnings and what GNOME Weather lacks (sunrise/sunset, wind); the per-place forecast (current conditions, hourly, 10-day) is dropped because GNOME Weather already shows it.
tags: [decision, scope, forecast, gnome-weather, roadmap]
generated: { by: claude-code/2.1.310, at: 2026-11-07T10:00:00Z }
sources:
  - id: gnome-weather
    resource: https://gitlab.gnome.org/GNOME/gnome-weather
    title: GNOME Weather source, main at b7de9e1 (2026-10-23)
---

# Status

Accepted (2026-11-07), decided by the project owner. Supersedes the
proposed [MOSMIX forecast source](forecast-source.md) and removes the
former milestone M5 – Forecasts from the [roadmap](../roadmap.md).

# Context

The [feature inventory](../features.md) copied WarnWetter's scope,
including per-place forecasts. WarnWetter is the only DWD app on its
platforms, but Phosh already ships GNOME Weather. It is adaptive and
runs on the phone. At main `b7de9e1` it shows, per place: the
condition icon, temperature, "feels like", an hourly and a daily
forecast. It has no radar, no nowcast, no warnings, no sunrise or
sunset, and no wind, humidity or pressure details.[^gnome-weather]
The app's visible name is **Weather Radar** ([app name](app-name.md)).

# Decision

- Cirro does not build what GNOME Weather already shows: no current
  conditions, no hourly forecast chart, no 10-day list. Milestone M5 –
  Forecasts is dropped; issues #14 and #23 are closed as not planned.
- Cirro focuses on radar, the point nowcast, official DWD warnings, more
  map layers and local notifications. These are the reasons to install
  Cirro next to GNOME Weather.
- Small additions that GNOME Weather lacks are allowed when they help
  with the questions the radar answers ("rain before dark?", "is a
  storm coming?") and come from DWD open data or local computation:
  - sunrise and sunset for the selected place, computed locally from
    the date and position (M6, #54);
  - wind: a wind map with arrows, and the wind at the selected place
    from the nearest DWD station (owner, 2026-11-07; M6, #58, #59). Source:
    [data sources](../data-sources.md), section 10.
- Temperature and the other current conditions *for a place* stay
  with GNOME Weather. As **map layers** they are in scope: GNOME
  Weather has no map, and the owner wants every useful DWD layer in
  Cirro (2026-11-07, [map layers](../map-layers.md)).

# Consequences

- No MOSMIX parser, station catalogue or `ww` icon table; one data
  path (DWD radar and warnings) less to keep alive.
- The milestone numbers stay: M6 – Extras keeps its name, so existing
  links stay valid. The owner closes or deletes the GitHub milestone
  "M5 – Forecasts".
- The facts about MOSMIX and Bright Sky stay in
  [data sources](../data-sources.md) in case the decision is revisited.
- If GNOME Weather drops its forecast or stops working on Phosh, this
  decision is to be revisited.
