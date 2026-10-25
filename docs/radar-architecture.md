---
type: Concept
title: Radar architecture
description: How Cirro fetches, decodes, caches, projects and animates RV nowcast frames on a libshumate map.
tags: [radar, architecture, nowcast, map, animation]
generated: { by: claude-code/2.1.310, at: 2026-10-24T23:50:00Z }
---

# Goal

One map screen, like WarnWetter's radar: base map, coloured
precipitation overlay, a time bar from about −60 min to +120 min in
5-min steps, play/pause, and drag to scrub. Forecast frames are marked
as such. Smooth at 360×720 on an aarch64 phone.

# Pipeline

```
RadarSource ──► FrameStore ──► Colorizer ──► RadarLayer (Shumate) ──► MapView
 (download)     (cache,         (values →     (draws texture at      + TimeBar
                 timeline)       RGBA)         projected bounds)
```

1. **RadarSource** (background thread, `Gio`/`Soup` async):
   - Every 5 min, conditional GET (`If-Modified-Since`) on
     `composite_rv_LATEST.tar` → 25 frames, analysis time *t0* and leads
     +0 … +120 min.
   - Past frames: the `_000` member of the older
     `composite_rv_<time>.tar` files (−5 … −60 min), fetched once and
     kept. It is the first tar entry, so two range requests (512-byte
     header, then the member) fetch it without the rest of the tar;
     tars stay available for 48 h ([data sources](data-sources.md)).
   - Stale guard: if *t0* is older than 30 min, show "radar data
     outdated" instead of silently showing old frames (this is exactly
     how other clients broke on 2026-10-20).
2. **Decoder**: read HDF5 `/dataset1/data1/data` (`uint32`) +
   `gain`/`offset`/`nodata`/`undetect` into mm/h (mm per 5 min × 12).
   Valid time from `/dataset1/what/enddate`+`endtime`, forecast flag
   from `/how/simulated`. Pure function, unit-tested with the recorded
   file in `tests/data/`.
3. **FrameStore**: ordered timeline `{valid_time: Frame}`, one source of
   truth for the UI; drops frames older than 3 h; persists the last
   download in `$XDG_CACHE_HOME` so the app opens instantly.
4. **Colorizer**: raw value → RGBA lookup table (65 536 entries,
   transparent below 0.1 mm/h). Produces one `Gdk.MemoryTexture` per
   frame in the reprojected grid (step 5), done once per frame, not per
   draw.
5. **Projection**: the RV grid is not Web Mercator. Instead of
   reprojecting per pixel on every draw, reproject **once per frame**
   into a Web-Mercator-aligned texture covering the composite's bounding
   box (inverse mapping with a precomputed index table, which is the
   same for every frame and computed once per grid definition).
6. **RadarLayer**: `Shumate.Layer` subclass that, in `snapshot()`, maps
   the texture's Mercator bounds to widget coordinates via the viewport
   and appends the texture with `snapshot.append_scaled_texture()`
   (linear filtering, a `Gsk.ScalingFilter.NEAREST` option for crisp
   cells at high zoom). Switching frames swaps one texture reference, so
   animation costs nothing besides a redraw.
7. **TimeBar**: `Gtk.Scale` with marks per 30 min, a "now" mark,
   play/pause button, label "Forecast +35 min" vs. "14:05"; playback via
   `GLib.timeout_add(400 ms)`, stops at the end and loops after a pause.

# Implementation status (M1)

M1 shows one static frame, the newest analysis (`_000`). Modules:

| Module | Step |
|---|---|
| `cirro/source.py` | Download: `Range: bytes=0-511` on `composite_rv_LATEST.tar` gives the first member's name and size; the member itself is then fetched from the timestamped tar named in it (immutable, so LATEST being replaced between the two requests does no harm). Falls back to slicing if a server ignores ranges. |
| `cirro/radar.py` | Decoder → `Frame` (`uint16` raw, gain/offset, times, forecast flag) and `Grid` (projdef, size, outer edges from the `UL` corner). |
| `cirro/projection.py` | Polar stereographic forward/inverse and Web Mercator in numpy (pyproj is not in the Flatpak); agrees with pyproj to < 1 mm. `reproject_grid()` builds the index table for a 1400-px-wide Mercator image (1400×1364, ≈ 1.2 km per pixel), cached per `Grid`. |
| `cirro/colors.py` | 65 536-entry RGBA lookup table on the raw value ([colour scale](decisions/colour-scale.md)). |
| `cirro/radar_layer.py` | `RadarLayer` computes the texture rectangle with `MapSource.get_x/get_y` like `shumate_viewport_location_to_widget_coords()` and applies the map rotation to the snapshot. Linear filtering below zoom 9, nearest from zoom 9. |
| `cirro/window.py` | Map, legend, reload button; loading runs in a thread, errors show a toast with "Retry". |

Timings on the x86_64 dev container: index table 0.5 s (once), colouring
40 ms per frame, member download 0.1–0.6 MB. Phone numbers follow in M2.

`Shumate.set_user_agent()` makes libshumate send the app's User-Agent
for tiles; libshumate's tile downloader keeps its own 100 MB file cache.

## Alignment check

On 2026-10-24 the 23:40 UTC analysis was compared with DWD's WMS
(`Radar_rv_product_1x1km_ger`, `EPSG:3857`, 512×512 px over
5.5–11.0 °E, 49.0–53.5 °N, ≈ 2 km per pixel): the WMS's yellow-and-above
area and our ≥ 3.0 mm/h area (threshold picked to match the area
fraction) agreed in **100 %** of pixels at zero offset and 98 % at
±1 px, so there is no systematic shift. A screenshot at zoom 9.5 over
the Jade Bight shows the cells following the coast.

# Point nowcast (M3)

The same FrameStore gives the value series at the user's cell (nearest
grid cell of the location, inverse projection) → bar chart of 25 values
and a sentence: "Rain from 14:20, heavy around 14:35" / "No rain
expected in the next 2 hours". No extra download.

# Memory and bandwidth budget

- 37 frames (−60 … +120 min) × 1200×1100 cells: as `float32` or as
  RGBA textures ≈ 195 MB each way, too much for a phone. Keep frames as
  the raw values narrowed to `uint16` (the file has `uint32`, but the
  largest value seen is 2333; keep `nodata` as 65535) + gain/offset
  (≈ 98 MB, less if cropped to the visible area) and colourise lazily around the current time position
  with a small LRU of textures (e.g. 8). Measure in M2.
- Bandwidth: `composite_rv_LATEST.tar` is 1.9–11 MB (measured in M0),
  so polling every 5 min costs up to ~130 MB per hour in wide rain. Poll
  only while the window is visible and on demand after resume, use
  `If-None-Match`, and consider range requests for individual members.
  Measure on the phone in M2.

# Fallback

If decoding RV turns out impractical (see the
[radar source decision](decisions/radar-source.md)), RadarSource can be
replaced by a WMS source that downloads pre-rendered PNGs per `TIME`
for the visible bounding box in `EPSG:3857`; the rest of the pipeline
(FrameStore, RadarLayer, TimeBar) stays unchanged, only Decoder and
Colorizer are skipped.
