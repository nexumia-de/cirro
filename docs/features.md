---
type: Concept
title: Feature inventory
description: The WarnWetter features Wetterblick replicates, ordered by priority, with the data each one needs.
tags: [features, scope, warnwetter]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Scope

WarnWetter is DWD's official weather and warning app. Wetterblick is a
lookalike in function, not in branding: its own name, icon and colours,
built only on DWD open data (see the
[data source decision](decisions/radar-source.md)).

Priorities: **P1** must have for the first usable release, **P2** next,
**P3** later or optional.

| Feature | Prio | Data | Milestone |
|---|---|---|---|
| Rain radar map: last ~1 h + forecast to +2 h, 5-min steps, play/pause, time scrubber | P1 | RV nowcast composite | [M1–M2](roadmap.md) |
| Own location on the radar map (GeoClue portal) | P1 | Location portal | M2 |
| Radar legend (mm/h colour scale), timestamp, "forecast" marker | P1 | – | M2 |
| Point nowcast: "Rain starts in 15 min", 2-h precipitation bar chart for a place | P1 | RV values at a cell | M3 |
| Saved places (search by name, current location) | P2 | Geocoding | M3 |
| Weather warnings for a place (list + map colouring) | P2 | DWD warnings | M4 |
| Current conditions and 10-day forecast per place | P2 | MOSMIX or Bright Sky | M5 |
| Hourly forecast chart (temperature, precipitation, wind) | P2 | MOSMIX | M5 |
| Other map layers: warnings, lightning, temperature, satellite | P3 | DWD GeoServer | M6 |
| Notifications for warnings and imminent rain | P3 | warnings + nowcast, background service | M6 |
| Pollen, UV, health forecasts | P3 | DWD open data | later |
| Widgets / lock screen | – | not available on Phosh | – |

# Explicitly out of scope

- Crowdsourced user reports (WarnWetter "Nutzermeldungen"): needs a
  backend.
- Push notifications via a server; notifications, if any, are polled
  locally (see [roadmap](roadmap.md), M6).
- Countries outside Germany for the radar: the RV composite covers
  Germany and a border strip only.
