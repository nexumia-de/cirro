---
type: Decision Record
title: CAP open data as warning source
description: Proposed - warnings per place come from DWD's CAP status files on open data; the WMS warning layer is only the optional map overlay.
tags: [decision, warnings, dwd, cap, wms, data]
generated: { by: claude-code/2.1.310, at: 2026-10-26T06:30:00Z }
---

# Status

Proposed (2026-10-26) for M4, issue
[#20](https://github.com/nexumia-de/cirro/issues/20). The owner decides.
Facts were checked against the live services on 2026-10-25
([data sources](../data-sources.md), section 4).

# Context

M4 needs, for every saved place: the current and upcoming official
warnings, a severity colour, a detail page with the full text, and
optionally a warning overlay on the map. Later (M6) a background
service may poll warnings for notifications. Constraints: no own backend
([decision](no-backend.md)), open data only, cache every response,
unchanged warnings keep the DWD source note, changed ones must not.

# Options

1. **CAP status on open data**:
   `weather/alerts/cap/COMMUNEUNION_DWD_STAT/…_LATEST_…_<lang>.zip`.
   - \+ Complete official content: event, severity 1–4, urgency,
     certainty, onset/expiry, headline, description, instruction,
     parameters, DWD colour; in German, English, French and Spanish.
   - \+ Polygons and warn cell ids are in the file: a point-in-polygon
     test finds the warnings of any saved place without another
     download, and the same polygons can draw the map overlay.
   - \+ One file for all places; `ETag` + `If-None-Match` (`304`) make
     an unchanged poll nearly free; works offline from the cached file.
   - \+ Standard format (CAP 1.2) with a documented profile; DWD's
     update logic cancels severe warnings explicitly.
   - − 0.2–0.8 MB per change, and the status changed 160–200 times a
     day on two windy days; polling every 5 min while open would fetch
     most of them. Needs a slower poll (e.g. 15 min) or the `DIFF`
     files (mostly 22 bytes) plus status handling.
   - − Own XML parsing (stdlib `zipfile` + `xml.etree`, no new module)
     and own point-in-polygon in numpy.
2. **WMS warning layers** (`Warnungen_Gemeinden_vereinigt` …).
   - \+ Ready-made transparent PNG overlay in the DWD colours,
     `EPSG:3857`, 58 KB per 512×512 tile.
   - − Pictures only: no text, no times, no list per place. The detail
     page would need `GetFeatureInfo` or the WFS anyway.
   - − German only; a new request per pan/zoom; no cache validators.
3. **WFS on the same GeoServer** (GeoJSON, `CQL_FILTER` by point or
   warn cell).
   - \+ Tiny per place (≈ 1 KB for two warnings), all CAP fields.
   - − One request per place per poll, German only, no `ETag`, no
     documented service level for WFS in DWD's product overview (only
     WMS is listed); GeoServer query syntax is an implementation detail.
4. **Bright Sky `/alerts`** (point → warnings, DE + EN).
   - \+ Simplest client; warn cell name included.
   - − Third-party, one maintainer, no SLA (it stalled for a day on
     2026-10-01); a warning service should not depend on it.

# Recommendation

Option 1, `COMMUNEUNION_DWD_STAT` in the UI language (`EN` or `DE`,
others as available), polled with `If-None-Match` while the app is open
(every 10–15 min; the M6 background service may use the `DIFF` files).
Match saved places by point-in-polygon on the CAP areas, honour
`<altitude>`/`<ceiling>` in the detail text ("above 1000 m"). Use the
CAP `severity` for the colour class and show it in words too, so colour
is never the only carrier.

For the optional map overlay, start with option 2
(`Warnungen_Gemeinden_vereinigt`, a second Shumate raster layer) because
it costs nothing to build; drawing the CAP polygons ourselves can
replace it later if the extra requests or the German-only legend become a
problem. Options 3 and 4 stay debugging aids.

# Consequences

- New module for CAP: download, unzip, parse, filter expired warnings,
  point-in-polygon per place; tested with recorded CAP zips in
  `tests/data/` (CC BY 4.0, DWD; geometry © GeoBasis-DE / BKG, in
  `REUSE.toml`).
- Warning texts are shown unchanged with "Source: Deutscher
  Wetterdienst"; when polygons are drawn, the BKG note from the CAP
  `LICENSE` code goes into the About dialog.
- Bandwidth: up to a few MB per hour on a stormy day while open; to be
  measured in M4 and tuned with the poll interval or `DIFF` files.
- The DWD profile reserves the right to change codes (`II` is not
  guaranteed numeric); the parser keys on `severity` and keeps `II` as a
  string.
