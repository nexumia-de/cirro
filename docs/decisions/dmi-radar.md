---
type: Decision Record
title: DMI as second radar source for Denmark
description: Proposed - add DMI's radar composite behind a radar provider interface after M3, chosen by location; past frames only, no forecast for Denmark.
tags: [decision, radar, dmi, denmark, data, architecture]
generated: { by: claude-code/2.1.310, at: 2026-10-26T06:30:00Z }
---

# Status

Proposed (2026-10-26) for issue
[#11](https://github.com/nexumia-de/cirro/issues/11) (backlog, no
milestone). The owner decides. **DMI facts are not verified live**:
every DMI host was blocked in the cloud environment on 2026-10-26
([data sources](../data-sources.md), section 8;
[dev environment](../dev-environment.md)). Verify them before accepting.

# Context

Issue #11 asks for more radar sources, starting with DMI, with the
source chosen by the user's location: DWD in Germany, DMI in Denmark.
DWD's RV composite ends at about 55.86 °N, i.e. it covers only the south
of Jutland. Cirro's pipeline is built around RV
([radar architecture](../radar-architecture.md)): a tar of 25 frames
(analysis + 2-h forecast) every 5 min, `uint32` precipitation per
5 min, a polar stereographic grid, one index table per grid, a
colour table on raw values and a time bar from −60 to +120 min.

What DMI offers, as documented:

| | DWD RV | DMI composite |
|---|---|---|
| Access | static files, `ETag`, ranges | STAC API (`opendataapi.dmi.dk`), one `.h5` per scan, no key, 500 req/5 s |
| Quantity | precipitation (mm per 5 min) | reflectivity, column max (dBZ) |
| Grid | 1 km, polar stereographic (`lat_0=90`) | 500 m, oblique stereographic (`lat_0=56`, `lon_0=10.5666`) |
| Cadence | 5 min | 5 min, alternating full-range (240 km) and Doppler (120 km) scans |
| Forecast | 0–120 min | none |
| Archive | 48 h | 180 days |
| Licence | CC BY 4.0, DWD | CC BY 4.0, DMI |

# Options

1. **Not now** (keep #11 in the backlog until M3 is done).
   - \+ No work before the core is finished; no second format to keep
     alive.
   - − Danish users see no radar north of 55.9 °N.
2. **DMI as a second provider, chosen by location**: a
   `RadarProvider` interface (list frames, fetch, decode to a common
   value, grid) with DWD RV and DMI implementations; the location (or
   the map centre) picks the provider by bounding box, DWD winning where
   both cover.
   - \+ Fulfils #11 with official data from both services; the
     FrameStore, renderer, RadarLayer and TimeBar stay.
   - − Denmark gets past frames only; the time bar and the M3 point
     nowcast ("rain starts in 15 min") have no data there. Own
     extrapolation (optical flow, as the third-party dmi-nowcast does)
     is heavy for a phone and would be Cirro's own forecast, not DMI's.
   - − dBZ needs a Z–R relation (e.g. Marshall–Palmer) to use the mm/h
     colour scale, and column-max reflectivity overstates rain; the
     legend has to say so.
   - − New projection math (oblique stereographic) in
     `cirro/projection.py`, a second index table, 500 m cells (larger
     textures), a STAC client, and one HTTP request per frame.
   - − The alternating Doppler scans cover a smaller area; using only
     the full-range scans gives a 10-min step, unlike DWD's 5 min.
3. **Both at once as a mosaic** (draw DMI under DWD).
   - \+ No visible switch at the border.
   - − Two downloads all the time, two time grids to align, and a
     visible seam in values (precipitation vs. converted reflectivity).

# Recommendation

Option 2, but **after M3** and after the DMI facts are verified live:
first allow the DMI hosts, record one composite in `tests/data/`, check
`h5dump` layout, projdef, size, cadence and real file size, and confirm
the terms and the credit line. Then introduce the `RadarProvider`
interface when the second implementation is written (not in advance,
per the toolkit's code-reuse rule). Use full-range scans only (10-min
step) unless the Doppler composite's area is enough for the user's
place. For Denmark the time bar ends at "Now" and the point nowcast
says that no forecast is available there; no own extrapolation.

# Consequences

- Needs `opendataapi.dmi.dk` (API and downloads) allowed in the dev
  environment, and `www.dmi.dk` for the documentation.
- `AGENTS.md` names "DWD open data, OSM" as the allowed sources; adding
  DMI extends that list (CC BY 4.0, redistributable) and needs a line
  there and in [data sources](../data-sources.md), section 7.
- Attribution "Source: DMI" (with the alteration note, since the data
  is reprojected, converted and coloured) next to the radar while DMI
  frames are shown, and in the About dialog with the CC BY 4.0 link.
- Location-based choice needs the location portal or the map centre;
  without either, Germany (DWD) stays the default.
- More data formats to keep alive: DWD changed its format without
  notice on 2026-10-20; the same can happen at DMI, so its decoder needs
  the same isolation, recorded test file and stale guard.
