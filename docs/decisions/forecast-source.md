---
type: Decision Record
title: MOSMIX directly as forecast source
description: Proposed - the per-place forecast reads DWD's MOSMIX_L single-station KMZ files; Bright Sky is not used in the app.
tags: [decision, forecast, mosmix, brightsky, dwd, data]
generated: { by: claude-code/2.1.310, at: 2026-10-26T06:30:00Z }
---

# Status

Proposed (2026-10-26) for M5, issue
[#23](https://github.com/nexumia-de/cirro/issues/23) (the view itself is
[#14](https://github.com/nexumia-de/cirro/issues/14)). The owner decides.
Facts were checked against the live services on 2026-10-25/26
([data sources](../data-sources.md), sections 3 and 5).

# Context

M5 shows per saved place: current conditions, an hourly chart
(temperature, precipitation, wind) and a 10-day list. Constraints: no
own backend ([decision](no-backend.md)), open data only, cache every
response, the app should keep working when a third party is down.

# Options

1. **MOSMIX_L directly**:
   `weather/local_forecasts/mos/MOSMIX_L/single_stations/<id>/kml/MOSMIX_L_LATEST_<id>.kmz`.
   - \+ Primary DWD source, same host and terms as the radar; 6 045
     stations worldwide (also Denmark, see
     [DMI radar](dmi-radar.md)).
   - \+ 18 KB per place and run, four runs a day, `ETag`/`304`: a
     refresh is nearly free; works offline from the cache.
   - \+ 247 hourly steps (≈ 10 days) and 114 elements, including
     probabilities (`wwP`, `R101` …) and present-weather codes `ww` for
     icons.
   - − Own parsing of KML (stdlib `zipfile` + `xml.etree`, no new
     module), unit conversion (K, Pa, m/s), a `ww` → icon/condition
     table, daily min/max from hourly values.
   - − Needs the station catalogue (300 KB) to find the nearest station;
     download it once and cache it.
   - − No observations: "current conditions" are the forecast for the
     current hour, unless the app also reads the hourly observation
     CSVs (`weather_reports/poi/<id>-BEOB.csv`, 974 stations).
2. **Bright Sky `/weather` + `/current_weather`**.
   - \+ One JSON call per place; observations merged in, derived
     `condition`/`icon`, metric units, nearest station chosen for us.
   - \+ Same underlying data (MOSMIX_L) and the DWD terms apply; "free
     to use for all purposes".
   - − Third-party service run by one person in spare time, no SLA
     (stalled for a day on 2026-10-01): the app would break when it
     does, and there would be two data paths (DWD for radar and
     warnings, Bright Sky for forecasts).
   - − 115 KB JSON per place for 11 days (gzip available), no cache
     validators, so every refresh is a full download.
   - − Station fallback and condition derivation are Bright Sky's logic,
     not DWD's; harder to explain differences to users.

# Recommendation

Option 1. Read `MOSMIX_L_LATEST_<id>.kmz` of the nearest station
(catalogue cached locally), refresh with `If-None-Match` after each run
(≈ 04:15, 10:15, 16:15, 22:15 UTC), and derive the hourly chart and the
10-day list from the same file. For current conditions, show the
forecast for the current hour first; adding the observation CSV of the
nearest observing station is a follow-up decision in M5. Bright Sky
remains useful while developing, to cross-check parsed values.

# Consequences

- New modules: station lookup, KMZ parser (tested with recorded KMZ
  files in `tests/data/`, CC BY 4.0 DWD), `ww` → icon mapping using
  symbolic icons from the icon theme (`weather-*-symbolic`).
- Attribution as for the radar: "Source: Deutscher Wetterdienst" next
  to the forecast (unchanged values), alteration note in the About
  dialog for derived daily values.
- The forecast is for a station, not the exact place: show the station
  name and distance in the detail view.
- If the parser turns out to be too much work, Bright Sky can be added
  behind the same interface later; the reverse would be harder.
