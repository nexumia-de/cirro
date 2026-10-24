---
type: Reference
title: Data sources
description: DWD open data products and other services Wetterblick uses, what is known about each and what still has to be verified.
tags: [data, dwd, radar, radvor, wms, warnings, mosmix, osm]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
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

Collected on 2026-10-24 from web research only: the cloud environment
blocked `opendata.dwd.de`, `maps.dwd.de` and `api.brightsky.dev` (see
[dev environment](dev-environment.md)). Everything marked **unverified**
must be checked against the live service in milestone M0 of the
[roadmap](roadmap.md), and this file updated with the result.

# 1. RADVOR RV nowcast composite (primary radar data)

DWD's radar nowcast: precipitation amount per 5 minutes on a ~1 km grid
over Germany, analysis plus forecast up to +2 h, refreshed every
5 minutes.[^dwd-radar-products][^ha-dwd-precip]

- Directory: `https://opendata.dwd.de/weather/radar/composite/rv/`.
- **Format change on 2026-10-20**: the old
  `DE1200_RV_LATEST.tar.bz2` (RADOLAN binary) stopped updating on
  2026-10-20 07:55 UTC and returns 404 since 2026-10-22. It is replaced
  by `composite_rv_YYYYMMDD_HHMM.tar` and `composite_rv_LATEST.tar`
  (plain, uncompressed tar).[^sdwf-40][^rain-warner-9] Libraries and
  blog posts older than that describe the dead format.
- Each tar holds 25 ODIM HDF5 files, suffixes `_000-hd5` … `_120-hd5`,
  i.e. lead times 0–120 min in 5-min steps.[^sdwf-40][^wetterdienst-3285]
- ODIM_H5/V2_3, `object=COMP`, quantity `ACRR` (accumulated
  precipitation), grid 1200×1100.[^wetterdienst-3285]
- A sibling product WN (reflectivity `DBZH`, same layout,
  `composite_wn__LATEST.tar` with two underscores) exists.[^wetterdienst-3285]

**Unverified, to determine in M0** (download one tar, inspect with
`h5dump -H`):

- HDF5 group paths (`/dataset1/data1/data`?), `gain`, `offset`,
  `nodata`, `undetect`, data type, compression filter.
- Projection (`/where/projdef`, presumably the DWD polar stereographic
  RADOLAN grid) and corner coordinates (`LL_lon` … `UR_lat`).
- Unit of `ACRR` (mm per 5 min expected) and size of one tar (bandwidth
  every 5 min on mobile data).
- Whether past frames (observations of the last hour) are only available
  as older `composite_rv_<time>.tar` files, i.e. the `_000` member of
  each, and how long they are kept.

# 2. DWD GeoServer WMS (pre-rendered radar images)

`https://maps.dwd.de/geoserver/dwd/wms` serves rendered radar maps with
a WMS `TIME` dimension. A third-party client reports 5-min frames, about
3 days of history and +2 h forecast via `Radar_*-product_*` layers, a
default layer `Niederschlagsradar` (mm/h) and
`Radar_wn-product_1x1km_ger` (dBZ) with nowcast frames.[^radar-card]

**Unverified**: layer names, `TIME` values for forecast frames,
`EPSG:3857` support, styles, terms of use. Check with `GetCapabilities`
in M0. This is the fallback radar source and the source for extra map
layers (warnings, lightning) in M6.

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
