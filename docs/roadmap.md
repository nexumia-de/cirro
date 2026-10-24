---
type: Plan
title: Roadmap
description: Milestones from the empty repository to a usable radar app (M0–M3) and the secondary features (M4–M6).
tags: [plan, roadmap, milestones]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Principle

Radar first. M0–M3 deliver the core: an animated rain radar with a
2-hour forecast and a point nowcast for the user's location. Warnings,
forecasts and notifications follow only after that works well on the
phone. Feature priorities: [feature inventory](features.md).

# M0 – Verify data and scaffold

- [ ] Allow the hosts from [dev environment](dev-environment.md).
- [ ] Download `composite_rv_LATEST.tar`, inspect with `h5dump -H`,
      record group paths, encoding, projection, corner coordinates, tar
      size and update cadence in [data sources](data-sources.md).
- [ ] Check how far back older `composite_rv_<time>.tar` files exist
      (past frames for the time bar).
- [ ] `GetCapabilities` of the DWD GeoServer WMS: radar layer names,
      forecast `TIME` values, `EPSG:3857`. Record the results.
- [ ] Check whether libshumate and h5py/numpy are in
      `org.gnome.Platform//51`; otherwise add them as manifest modules
      (see [map decision](decisions/map-libshumate.md)).
- [ ] Confirm or revise the [radar source decision](decisions/radar-source.md).
- [ ] Scaffold: Python package `wetterblick/`, meson build, `.desktop`
      (`X-Purism-FormFactor=Workstation;Mobile;`), metainfo with
      `display_length ≥ 360` and touch, icon, Flatpak manifest
      `io.github.suitably.Wetterblick.yml`, Flatpak CI calling the
      toolkit workflow, `tests/` with pytest.
- [ ] Empty adaptive window passes the 360×720 screenshot check;
      `appstreamcli validate`, `desktop-file-validate` clean; CI green on
      x86_64 and aarch64.

# M1 – Map with a static radar frame

- [ ] `Shumate.SimpleMap` with OSM raster tiles, attribution, own
      User-Agent, tile cache; initial view Germany.
- [ ] Decoder for one RV HDF5 member, unit-tested with a recorded file.
- [ ] Colorizer (mm/h LUT) and one-time reprojection to Web Mercator.
- [ ] `RadarLayer` draws the current frame correctly aligned (check
      alignment against borders/coasts at high zoom).
- [ ] Legend.

# M2 – Animated radar with forecast (core feature)

- [ ] RadarSource with 5-min refresh, conditional requests, stale guard.
- [ ] FrameStore with past frames (−60 min) and forecast (+120 min),
      disk cache for instant start.
- [ ] TimeBar: scrub, play/pause, "now" mark, forecast labelling.
- [ ] Own location via the location portal (GeoClue), "centre on me".
- [ ] Measure memory, CPU and bandwidth on the phone; tune the texture
      LRU and polling. Record numbers in
      [radar architecture](radar-architecture.md).
- [ ] **First release**: Flatpak bundle installed on the phone.

# M3 – Point nowcast and places

- [ ] Value series at a location from the FrameStore → 2-h bar chart
      and a "rain starts in N min" sentence.
- [ ] Saved places: search (Nominatim, with its usage policy), current
      location, list in an `AdwNavigationSplitView` sidebar that
      collapses on the phone.
- [ ] Tap on the map shows the nowcast for that point.

# M4 – Warnings

- [ ] Choose warning product (CAP open data vs. WMS), record as a
      decision.
- [ ] Warnings per saved place, severity colours, detail page.
- [ ] Optional warning overlay on the map.

# M5 – Forecasts

- [ ] Choose MOSMIX directly vs. Bright Sky `/weather`, record as a
      decision.
- [ ] Current conditions, hourly chart, 10-day list per place.

# M6 – Extras

- [ ] Further map layers (lightning, temperature, satellite) via WMS.
- [ ] Local notifications for warnings and imminent rain, polled by a
      background portal/autostart service; battery impact measured.

# Risks

- **Data format churn**: DWD changed the RV format on 2026-10-20
  without a notice we could find. Keep the decoder isolated, test it
  with recorded files and fail visibly (stale guard).
- **Phone performance**: reprojection and colouring of 37 frames on
  aarch64 in Python; mitigated by numpy vectorisation and one-time index
  tables, measured in M2.
- **Flatpak size**: h5py + numpy + HDF5 add tens of MB. Alternative:
  the WMS fallback, which needs neither.
- **OSM tile policy**: fine for personal use; switch providers if usage
  grows.
