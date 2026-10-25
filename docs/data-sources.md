---
type: Reference
title: Data sources
description: DWD open data products and other services Cirro uses, what is known about each and what still has to be verified.
tags: [data, dwd, radar, radvor, wms, warnings, mosmix, osm]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:40:00Z }
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
  - id: osm-tile-policy
    resource: https://operations.osmfoundation.org/policies/tiles/
    title: OSMF tile usage policy
---

# Status of this file

Sections 1 and 2 were checked against the live services on 2026-10-24
around 21:15 UTC (milestone M0 of the [roadmap](roadmap.md)); facts
marked *(live)* come from that check, footnoted facts from web research.
Sections 3–6 are still from web research only.

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
  rain) seen within 48 h. Polling LATEST every 5 min therefore costs up
  to ~130 MB per hour on a rainy day.
- The server sends `ETag`, `Last-Modified` and `Accept-Ranges: bytes`;
  `If-Modified-Since` and `If-None-Match` both return `304`.
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
rain".[^breezy-3010] `/weather` and `/current_weather` give forecasts
from MOSMIX. Useful as a fallback and for quick prototyping of the point
nowcast; it is a third-party service with no SLA (it stalled for a day
on 2026-10-01).[^breezy-3010]

# 4. Warnings (M4)

DWD publishes warnings as open data (CAP files under
`https://opendata.dwd.de/weather/alerts/`) and as WMS layers. Exact
product and format to be chosen in M4.

# 5. Forecasts (M5)

MOSMIX station forecasts (KMZ/KML under
`https://opendata.dwd.de/weather/local_forecasts/mos/`) or Bright Sky
`/weather`, which wraps MOSMIX as JSON. Decide in M5.

# 6. Base map

OpenStreetMap raster tiles through libshumate (see the
[map decision](decisions/map-libshumate.md)). The OSMF tile policy
requires a valid `User-Agent`, attribution, client-side caching and no
bulk or offline prefetching.[^osm-tile-policy] If that becomes a
problem, switch to another tile provider; the tile URL is a setting.

[^dwd-radar-products]: DWD, Radar products
[^sdwf-40]: simple_dwd_weatherforecast #40
[^rain-warner-9]: ha-rain-warner #9
[^wetterdienst-3285]: wetterdienst #3285
[^ha-dwd-precip]: ha-dwd-precipitation README
[^breezy-3010]: breezy-weather #3010
[^radar-card]: weather-radar-card v3.4.0 release notes
[^osm-tile-policy]: OSMF tile usage policy
