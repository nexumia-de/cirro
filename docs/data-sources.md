---
type: Reference
title: Data sources
description: DWD open data products and other services Cirro uses, what is known about each and what still has to be verified.
tags: [data, dwd, radar, radvor, wms, warnings, cap, mosmix, brightsky, dmi, osm]
generated: { by: claude-code/2.1.310, at: 2026-10-26T06:30:00Z }
sources:
  - id: dwd-radar-products
    resource: https://www.dwd.de/EN/ourservices/radar_products/radar_products.html
    title: DWD, Radar products
  - id: sdwf-40
    resource: https://github.com/FL550/simple_dwd_weatherforecast/issues/40
    title: "simple_dwd_weatherforecast #40: DE1200_RV_LATEST.tar.bz2 is no longer updated"
  - id: rain-warner-9
    resource: https://github.com/nodomain/ha-rain-warner/issues/9
    title: "ha-rain-warner #9: DWD switched RV composite to new files"
  - id: wetterdienst-3285
    resource: https://github.com/earthobservations/wetterdienst/pull/3285
    title: "wetterdienst #3285: read the ODIM HDF5 layout of the composites"
  - id: ha-dwd-precip
    resource: https://github.com/Hoffmann77/ha-dwd-precipitation
    title: ha-dwd-precipitation (RADVOR RS/RV, HymecNG usage)
  - id: breezy-3010
    resource: https://github.com/breezy-weather/breezy-weather/issues/3010
    title: "breezy-weather #3010: Bright Sky precipitation nowcasting"
  - id: radar-card
    resource: https://github.com/jpettitt/weather-radar-card/releases/tag/v3.4.0
    title: weather-radar-card v3.4.0 release notes (DWD WMS layers)
  - id: dwd-legal
    resource: https://www.dwd.de/DE/service/rechtliche_hinweise/rechtliche_hinweise_node.html
    title: DWD legal notice (Rechtliche Hinweise)
  - id: dwd-source
    resource: https://www.dwd.de/EN/service/legal_notice/templates_dwd_as_source.html
    title: DWD rules for acknowledging the DWD as source
  - id: osm-tile-policy
    resource: https://operations.osmfoundation.org/policies/tiles/
    title: OSMF tile usage policy
  - id: dwd-warn-overview
    resource: https://www.dwd.de/DE/leistungen/opendata/help/warnungen/dwd_warnings_products_overview_en_pdf.pdf
    title: DWD, Product overview DWD Alerts (2020-02-20)
  - id: dwd-cap-profile
    resource: https://www.dwd.de/DE/leistungen/opendata/help/warnungen/cap_dwd_profile_en_pdf_2_1_14.pdf
    title: DWD, CAP DWD profile v2.1.14 (2023-10-17)
  - id: dwd-warn-codes
    resource: https://www.dwd.de/DE/leistungen/opendata/help/warnungen/warning_codes_pdf.pdf
    title: DWD, warning event codes and levels (2024-02-01)
  - id: dwd-mosmix-catalog
    resource: https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication&nn=16102
    title: DWD, MOSMIX station catalogue
  - id: brightsky-home
    resource: https://brightsky.dev/
    title: Bright Sky home page (terms section)
  - id: dmi-radar-data
    resource: https://www.dmi.dk/friedata/dokumentation/radar-data
    title: DMI, Radar Data (free data documentation)
  - id: dmi-radar-api
    resource: https://www.dmi.dk/friedata/dokumentation/radar-data-api
    title: DMI, Radar Data API
  - id: dmi-auth
    resource: https://www.dmi.dk/friedata/dokumentation/authentication
    title: DMI, Authentication (API keys dropped on 2025-12-02)
  - id: dmi-terms
    resource: https://www.dmi.dk/friedata/dokumentation/terms-of-use
    title: DMI, Terms of Use (CC BY 4.0)
  - id: dmi-nowcast
    resource: https://github.com/fink42/dmi-nowcast
    title: "dmi-nowcast: third-party STEPS nowcast from DMI composites (README, fetch.py, parse.py, geo.py)"
---

# Status of this file

Sections 1 and 2 were checked against the live services on 2026-10-24
around 21:15 UTC (milestone M0 of the [roadmap](roadmap.md)); facts
marked *(live)* come from that check, footnoted facts from web research.
Section 3 (Bright Sky), 4 (warnings) and 5 (forecasts) were checked
against the live services on 2026-10-25 20:45 UTC – 2026-10-26 06:00 UTC
for the M4/M5 decisions. Section 6 is from web research only. Section 7
was checked against the live DWD pages on 2026-10-25. Section 8 (DMI) is
from DMI's documentation as quoted by web search and from third-party
code only: every DMI host was blocked in the cloud environment
(proxy `403`, 2026-10-26), so nothing in it is verified live.

# 1. RADVOR RV nowcast composite (primary radar data)

DWD's radar nowcast: precipitation amount per 5 minutes on a 1 km grid
over Germany, analysis plus forecast up to +2 h, refreshed every
5 minutes.[^dwd-radar-products][^ha-dwd-precip]

- Directory: `https://opendata.dwd.de/weather/radar/composite/rv/`.
- **Format change on 2026-10-20**: the old
  `DE1200_RV_LATEST.tar.bz2` (RADOLAN binary) stopped updating on
  2026-10-20 07:55 UTC and returns 404 since 2026-10-22. It is replaced
  by `composite_rv_YYYYMMDD_HHMM.tar` and `composite_rv_LATEST.tar`
  (plain, uncompressed tar).[^sdwf-40][^rain-warner-9] Libraries and
  blog posts older than that describe the dead format.
- A sibling product WN (reflectivity `DBZH`, same layout,
  `composite_wn__LATEST.tar` with two underscores) exists.[^wetterdienst-3285]

## Files and update cadence *(live)*

- `composite_rv_LATEST.tar` is a copy of the newest timestamped tar
  (same size and `Last-Modified`). Files appear about 3–4 min after
  their nominal time (`…_2110.tar` at 21:13:21 UTC).
- The directory keeps **48 hours** of timestamped tars (576 files,
  oldest `composite_rv_20261022_2115.tar` on 2026-10-24 21:15), so past
  frames for the time bar are available.
- Tar size depends on the weather: **1.9 MB** (dry) to **11 MB** (wide
  rain) seen within 48 h; 11.6 MB on 2026-10-25 at 11:55 UTC. Polling LATEST every 5 min therefore costs up
  to ~130 MB per hour on a rainy day.
- The server sends `ETag`, `Last-Modified` and `Accept-Ranges: bytes`;
  `If-Modified-Since` and `If-None-Match` both return `304`. Combined
  with `Range: bytes=0-511`, a matching `If-None-Match` also returns
  `304` and a different one `206` (checked 2026-10-25), which is how
  Cirro polls.
- **Range requests work** (`206`): the `_000` member is the first entry
  of every tar, so a past frame needs only the 512-byte tar header
  (`Range: bytes=0-511`, gives the member size) and then
  `bytes=512-(511+size)`, about 0.1–0.5 MB instead of the whole tar.

## Tar contents *(live)*

- 25 members `composite_rv_<YYYYMMDD_HHMM>_<lead>-hd5`, lead
  `000` … `120` in 5-min steps, each 80–460 KB (561 KB seen for the
  23:40 UTC analysis on 2026-10-24 in wide rain).
- `/what`: `object=COMP`, `date`/`time` = analysis time (same in all 25
  members), `version=H5rad 2.3`; `/@Conventions=ODIM_H5/V2_3`.
- `/dataset1/what`: `startdate`/`starttime` … `enddate`/`endtime` is
  the 5-min accumulation interval; `endtime` is the valid time
  (analysis + lead). `prodname=RV_top_view`, `product=MAX`.
- `/how/simulated`: `"False"` for lead 000, `"True"` for forecasts.
  `/how/nodes` lists the 17 radar sites; `incomplete_nodes` and
  `missing_nodes` are empty strings when all sites deliver.
- Data: `/dataset1/data1/data`, **`uint32`**, shape **(1200, 1100)**
  (rows × columns), one gzip-6 chunk.
- `/dataset1/data1/what`: `quantity=ACRR`, `gain=0.001`,
  `offset=-0.001`, `nodata=4294967295` (2³²−1, outside the radar
  coverage, about 47 % of the grid), `undetect=0` (no precipitation).
  Value in mm per 5 min = raw × gain + offset. Maximum seen: raw 2333
  (2.3 mm per 5 min), so values fit in `uint16`.

## Grid and projection *(live)*

- `/where/projdef`: `+proj=stere +lat_ts=60 +lat_0=90 +lon_0=10
  +x_0=543196.83521776402 +y_0=3622588.8619310022 +units=m +a=6378137
  +b=6356752.3142451802 +no_defs` (polar stereographic on WGS84, the
  catalog path is `DWD/DE1200_WGS84/RV`).
- `xsize=1100`, `ysize=1200`, `xscale=yscale=1000` m.
- Corners (degrees): UL 55.8621 N 1.4633 E, UR 55.8454 N 18.7316 E,
  LL 45.6964 N 3.5670 E, LR 45.6846 N 16.5809 E.
- Projecting the corners with pyproj gives x/y = (−500, 500),
  (1099500, 500), (−500, −1199500), (1099500, −1199500): the grid spans
  x ∈ [−500, 1099500] m and y ∈ [−1199500, 500] m, i.e. the corner
  coordinates are the **outer edges**, offset half a cell from the
  origin. Row 0 is the northern edge (all `nodata`, as is the last row).
- A recorded member is in `tests/data/composite_rv_20261024_2110_000-hd5`;
  `tests/test_rv_sample.py` pins this layout.

# 2. DWD GeoServer WMS (pre-rendered radar images)

`https://maps.dwd.de/geoserver/dwd/wms` *(live, `GetCapabilities` 1.3.0,
988 KB)*:

- Service `AccessConstraints`: `https://www.dwd.de/copyright`, `Fees`:
  none.
- CRS list includes `EPSG:3857` (and `EPSG:4326`, `EPSG:25832`, …).
- Radar layers (all with style of the same name in lower case):
  - `Radar_rv_product_1x1km_ger` "Deutsches Radarkomposit Analyse und
    Vorhersage (RV)": dimension `time`
    `2026-10-21T00:00Z/2026-10-24T23:10Z/PT5M` (≈ 3.5 days back to +2 h),
    default `current`, plus `REFERENCE_TIME` (default = latest analysis).
  - `Niederschlagsradar`: same dimensions as the RV layer.
  - `Radar_wn-product_1x1km_ger` (reflectivity, analysis + forecast) and
    `Radar_wn-analysis_1x1km_ger` (analysis only, no forecast).
  - `Radar_eucom_zeros`: no-data/no-echo mask.
- `GetMap` with `layers=dwd:Radar_rv_product_1x1km_ger`,
  `crs=EPSG:3857`, `TIME=<analysis + 120 min>`, 512×512 PNG works
  (`200`, RGBA, ~45 KB). The image is **not** transparent where it is
  dry: "no echo" is painted white and the area outside coverage grey, so
  as a map overlay it needs a different style or post-processing.
- Its rendering of the RV layer lines up pixel-exactly with our own
  reprojection of the same frame; its yellow class starts at about
  3 mm/h (M1 alignment check in [radar architecture](radar-architecture.md)).

This is the fallback radar source and the source for extra map layers
(warnings, lightning) in M6.

# 3. Bright Sky API (point values, JSON)

`https://api.brightsky.dev/radar?lat=…&lon=…&distance=…` returns the RV
composite around a point as JSON; `precipitation_5` in 0.01 mm per
5 min, 5-min steps, 2 h forecast only when `last_date` is set (default
1 h). Cells outside the coverage return 0, which looks like "no
rain".[^breezy-3010] It is a third-party service with no SLA (it stalled
for a day on 2026-10-01).[^breezy-3010]

## `/weather`, `/current_weather`, `/alerts` *(live, 2026-10-25/26)*

- No API key. Terms on the home page: "free-to-use for all purposes";
  "the DWD's Terms of Use apply to all data you retrieve through the
  API".[^brightsky-home] Maintained by one person in spare time.
- `/weather?lat=50.11&lon=8.68&date=2026-10-25&last_date=2026-11-05`
  (Frankfurt): 263 hourly records from 2026-10-25T00:00Z to
  2026-11-04T22:00Z, 115 KB JSON (gzip served on request). Past hours
  come from observation stations (`observation_type: current`), future
  hours from the nearest MOSMIX station (`forecast`, here
  "FRANKFURT-SACHSENH." 1.1 km away); `sources` lists each one, and
  `fallback_source_ids` names a second station for fields the first
  lacks. Fields: temperature, dew point, humidity, pressure, wind
  speed/direction/gusts, cloud cover, visibility, precipitation,
  `precipitation_probability`, sunshine, solar, plus a derived
  `condition` and `icon` (e.g. `rain`, `cloudy`). Units are metric
  (°C, km/h, mm).
- Outside Germany it uses the same worldwide MOSMIX stations:
  Copenhagen returned observations from "KOPENHAGEN" and "MALMO" and the
  forecast of "KOPENHAGEN" (8.4 km).
- `/current_weather` merges the last 10/30/60-min observations of the
  nearest stations into one record (2 KB).
- `/alerts?lat=…&lon=…` returns the DWD warnings for the warn cell of
  the point in German and English (headline, description, instruction,
  severity, onset/expires, `event_code` = DWD `II`) plus the cell
  (`warn_cell_id`, name, district).
- No `ETag`, `Last-Modified` or `Cache-Control` headers: the app has
  to cache by its own rules.

# 4. Warnings (M4) *(live, 2026-10-25 20:45 UTC)*

DWD publishes its official warnings as CAP 1.2 XML on open data, as WMS
and WFS layers of the GeoServer, and as a JSON file.[^dwd-warn-overview]

## CAP on open data

- Base `https://opendata.dwd.de/weather/alerts/cap/` with 12
  directories: `{COMMUNEUNION,DISTRICT}_{DWD,CELLS,EVENT}_{STAT,DIFF}`.
  `COMMUNEUNION` = fused municipality areas, `DISTRICT` = districts;
  `DWD` = cell-based with DWD update logic (severe warnings are
  cancelled explicitly), `CELLS` = cell-based neutral logic, `EVENT` =
  event-based; `STAT` = full current status, `DIFF` = changes
  only.[^dwd-warn-overview]
- Files: `Z_CAP_C_EDZW_<yyyyMMddHHmmss>_PVW_STATUS_PREMIUMDWD_COMMUNEUNION_<lang>.zip`,
  `<lang>` = `DE`, `EN`, `FR`, `ES`, `MUL` (all languages in one, ~4 MB),
  plus a `…_LATEST_…` copy per language. The server sends `ETag` and
  `Last-Modified`; `If-None-Match` returns `304`.
- Cadence: a new file whenever warnings change; 162 (2026-10-24) and
  204 (2026-10-25 until 20:45 UTC) `DE` status files per day in
  `COMMUNEUNION_DWD_STAT`. The directory keeps about 48 h (oldest
  2026-10-23 20:56 UTC).
- Size of one `DE` status zip: 0.18–0.78 MB in those two windy days
  (1.3 MB unpacked for 39 warnings on 2026-10-25 20:44 UTC). `DIFF`
  zips are mostly empty (22 bytes, median), up to 0.39 MB.
- One XML file per warning (`<identifier>` `2.49.0.0.276.0.DWD.PVW.<ms>.<uuid>.DEU`).
  `<msgType>` `Alert` or `Update` (with `<references>`), `<status>`
  `Actual`; `<info>` has `<event>` (e.g. `STURMBÖEN` / EN `gale-force gusts`),
  `<severity>` `Minor`/`Moderate`/`Severe`/`Extreme` (= levels 1–4,
  yellow/orange/red/dark pink), `<urgency>`, `<certainty>`
  (`Observed`/`Likely`), `<onset>`, `<expires>`, `<headline>`,
  `<description>`, `<instruction>`, `<parameter>`s (e.g. `gusts`
  `65-85 [km/h]`), and `<eventCode>`s `II` (event type, e.g. 52; the
  profile says not to assume it is a number), `GROUP` (`WIND`, …),
  `AREA_COLOR` (DWD's RGB, e.g. `251 140 0`), `PROFILE_VERSION`
  `2.1.14` and `LICENSE` `© GeoBasis-DE / BKG 2021 (Daten modifiziert)`
  (the geometry's licence).[^dwd-cap-profile][^dwd-warn-codes]
- Each `<area>` carries a `<polygon>` (lat,lon pairs), `<geocode>`
  `WARNCELLID` (e.g. `809272121`), `<altitude>`/`<ceiling>` in feet
  (e.g. warnings above 1000 m only). Warning a saved place therefore
  needs only a point-in-polygon test on the CAP itself; no extra
  geometry download.
- The warn cell list `cap_warncellids_csv.csv` (11 828 cells: id, name,
  short name, state) and shapefiles for municipalities, districts,
  coast and sea are on DWD's open data help page.

## GeoServer WMS/WFS

- WMS layers (GetCapabilities): `Warnungen_Gemeinden`,
  `Warnungen_Gemeinden_vereinigt`, `Warnungen_Landkreise`,
  `Warnungen_Kueste`, `Warnungen_Binnenseen`, all queryable, no `time`
  dimension (current status only), German only; plus the warn area
  outlines `Warngebiete_*`.
- `GetMap` of `dwd:Warnungen_Gemeinden_vereinigt`, `EPSG:3857`,
  512×512 PNG, `transparent=true`: `200`, 58 KB, transparent outside
  warnings (unlike the radar layer), warning areas in the DWD colours
  at 80–96 % opacity.
- WFS on the same server (`/geoserver/dwd/ows?service=WFS`,
  `outputFormat=application/json`) returns the warnings as GeoJSON with
  all CAP fields as properties (`WARNCELLID`, `EVENT`, `SEVERITY`,
  `EC_II`, `ONSET`, `EXPIRES`, `HEADLINE`, `DESCRIPTION`,
  `INSTRUCTION`, `EC_AREA_COLOR`, …). Filtering works:
  `CQL_FILTER=INTERSECTS(THE_GEOM,POINT(53.97 9.23))` (lat lon) or
  `CQL_FILTER=WARNCELLID=801051012` with `propertyName=…` gave 2
  warnings in 0.8–1 KB (0.6 s). No `ETag`/`Last-Modified`.
- `https://www.dwd.de/DWD/warnungen/warnapp/json/warnings.json` is
  listed in DWD's open data product overview (districts, German, no
  polygons).[^dwd-warn-overview] Not checked further: its path belongs
  to the warning app and CAP covers the same content.

## Attribution

Warnings are DWD geodata under CC BY 4.0 (section 7). Shown unchanged,
they carry "Source: Deutscher Wetterdienst"; changed warnings must not
carry the DWD source note.[^dwd-source] Drawing the polygons also uses
BKG geometry, whose note is in the CAP `LICENSE` code.

# 5. Forecasts (M5) *(live, 2026-10-25/26)*

## MOSMIX on open data

- `https://opendata.dwd.de/weather/local_forecasts/mos/` has
  `MOSMIX_L`, `MOSMIX_S` and `MOSMIX-SNOW_S`.
- **MOSMIX_L**: four runs a day (files `…_2026102503`, `…09`, `…15`,
  `…21`, published about 1 h 15 min after the run hour, e.g. 04:16 UTC).
  `single_stations/<id>/kml/MOSMIX_L_LATEST_<id>.kmz` exists for 6 045
  stations worldwide (Frankfurt `10637`, Copenhagen `06180`); one KMZ is
  18 KB (344 KB KML inside, ISO-8859-1). `ETag`/`Last-Modified`, and
  `If-None-Match` returns `304`. `all_stations/` has one KMZ of 81–84 MB
  per run.
- The KML of 2026-10-25 15 UTC for Frankfurt: issuer DWD, models ICON
  12 UTC and ECMWF/IFS 00 UTC, **247 hourly steps** (2026-10-25 16:00Z
  to 2026-11-04 22:00Z, about 10 days), **114 elements** (`TTT`
  temperature in K, `Td`, `TX`/`TN`, `FF`/`DD`/`FX1` wind in m/s, `PPPP`
  pressure in Pa, `N` cloud cover, `ww` present weather code, `RR1c`
  precipitation, `wwP`/`R101`… probabilities, `SunD1` sunshine, `VV`
  visibility, …), station name and coordinates `8.6,50.05,111.0`.
- **MOSMIX_S**: hourly runs but only as one all-stations KMZ of about
  37 MB per run, so not usable on a phone.
- The station catalogue (id, name, position, height) is a 300 KB text
  file on www.dwd.de.[^dwd-mosmix-catalog]
- Observations for "current conditions": `weather/weather_reports/poi/<id>-BEOB.csv`
  for 974 stations, hourly, German headers, decimal comma
  (e.g. `10637-BEOB.csv`).

## Bright Sky `/weather`

Wraps exactly these MOSMIX_L forecasts and the observations as JSON
around a point; see section 3.

# 6. Base map

OpenStreetMap raster tiles through libshumate (see the
[map decision](decisions/map-libshumate.md)). The OSMF tile policy
requires a valid `User-Agent`, attribution, client-side caching and no
bulk or offline prefetching.[^osm-tile-policy] If that becomes a
problem, switch to another tile provider; the tile URL is a setting.

# 7. Licences and attribution *(live, 2026-10-25)*

- DWD: all freely accessible geodata and geodata services may be reused
  under **CC BY 4.0** with a source note.[^dwd-legal] Geodata includes
  all meteorological weather and climate information with a location.
- The source note goes **immediately next to the information used**:
  "Source: Deutscher Wetterdienst" for unchanged data. For processed
  data DWD expects an alteration note such as "Based on data from
  Deutscher Wetterdienst, gridded data reproduced graphically", and at
  least a mention in a central list of references.[^dwd-source] Changed
  official warnings must not carry the DWD source note (relevant for
  M4).
- Cirro reprojects and colours the RV grid. The map shows "Based on
  data from Deutscher Wetterdienst" next to the radar (`cirro/window.py`);
  the full alteration note "…, gridded data reproduced graphically" did
  not fit next to the scale bar at 360 px, so it is in the About dialog
  (the central list of references DWD expects for processed data) with
  the CC BY 4.0 link (`cirro/main.py`). Text form only: no DWD logo (see
  `AGENTS.md`).
- OSM: "© OpenStreetMap contributors" on the map (libshumate's licence
  widget) and in the About dialog, with a link to the ODbL copyright
  page.
- Recorded DWD sample data in `tests/data/` is marked `CC-BY-4.0`,
  copyright Deutscher Wetterdienst, in `REUSE.toml`.

# 8. DMI radar (Denmark) *(not verified live)*

All DMI hosts (`opendataapi.dmi.dk`, `dmigw.govcloud.dk`, `www.dmi.dk`,
`opendatadocs.dmi.govcloud.dk`) were blocked in the cloud environment
on 2026-10-26 (proxy `403`), so these facts come from DMI's
documentation as quoted by web search and from a third-party client.
Verify them before building on them.

- API: `https://opendataapi.dmi.dk/v1/radardata/collections/{composite,pseudoCappi,volume}/items`,
  STAC GeoJSON; each feature's `asset` (singular) links an `.h5` file
  under `/v1/radardata/download/`. Query by `datetime`, `bbox`,
  `scanType`, `limit`; only `sortorder=datetime,DESC` is
  accepted.[^dmi-radar-api][^dmi-nowcast] 180 days of
  archive.[^dmi-radar-api]
- No API key since 2025-12-02 on `opendataapi.dmi.dk`; the old host
  `dmigw.govcloud.dk` still needs one. Rate limit 500 requests per 5 s
  (`429` above), fair use applies.[^dmi-auth]
- Composite: all Danish radars, maximum where they overlap, **every
  5 min**, 500 m pixels; minutes 0, 10, … from full-range scans
  (240 km), minutes 5, 15, … from Doppler scans (120 km, smaller
  area). Example file `dk.com.<YYYYMMDDHHMM>.500_max.h5`, bounding box
  about 4.38–20.74 °E, 52.29–59.83 °N. Pseudo-CAPPI per radar every
  10 min.[^dmi-radar-data]
- Format: HDF5 after OPERA ODIM, version 2.0 for composites, but with
  the scaling (`gain`, `offset`, `nodata`, `undetect`) and `product=DBZH`
  in the root `/what` group.[^dmi-radar-data][^dmi-nowcast] The values
  are **reflectivity in dBZ (column maximum)**, not precipitation, so a
  Z–R relation is needed for mm/h.[^dmi-nowcast]
- Projection: `+proj=stere +lat_0=56 +lon_0=10.5666 +lat_ts=56` on
  WGS84, an **oblique** stereographic projection (DWD's RV uses the
  polar one, `lat_0=90`).[^dmi-nowcast]
- No radar nowcast or forecast product was found in DMI's open data;
  the third-party dmi-nowcast project computes its own by optical flow
  and STEPS.[^dmi-nowcast] DMI's open forecast data are NWP fields
  (HARMONIE DINI, 2 km, every 3 h).
- Licence: CC BY 4.0; credit, link to the licence, and indicate
  changes.[^dmi-terms]

[^dwd-radar-products]: DWD, Radar products
[^sdwf-40]: simple_dwd_weatherforecast #40
[^rain-warner-9]: ha-rain-warner #9
[^wetterdienst-3285]: wetterdienst #3285
[^ha-dwd-precip]: ha-dwd-precipitation README
[^breezy-3010]: breezy-weather #3010
[^radar-card]: weather-radar-card v3.4.0 release notes
[^osm-tile-policy]: OSMF tile usage policy
[^dwd-legal]: DWD legal notice (Rechtliche Hinweise)
[^dwd-source]: DWD rules for acknowledging the DWD as source
[^dwd-warn-overview]: DWD, Product overview DWD Alerts
[^dwd-cap-profile]: DWD, CAP DWD profile v2.1.14
[^dwd-warn-codes]: DWD, warning event codes and levels
[^dwd-mosmix-catalog]: DWD, MOSMIX station catalogue
[^brightsky-home]: Bright Sky home page
[^dmi-radar-data]: DMI, Radar Data
[^dmi-radar-api]: DMI, Radar Data API
[^dmi-auth]: DMI, Authentication
[^dmi-terms]: DMI, Terms of Use
[^dmi-nowcast]: dmi-nowcast (fink42)
