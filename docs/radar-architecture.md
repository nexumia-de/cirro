---
type: Concept
title: Radar architecture
description: How Wetterblick fetches, decodes, caches, projects and animates RV nowcast frames on a libshumate map.
tags: [radar, architecture, nowcast, map, animation]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
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
     kept. To be confirmed in M0 ([data sources](data-sources.md)).
   - Stale guard: if *t0* is older than 30 min, show "radar data
     outdated" instead of silently showing old frames (this is exactly
     how other clients broke on 2026-10-20).
2. **Decoder**: read HDF5 `data` + `gain`/`offset`/`nodata`/`undetect`
   into a `float32` array in mm/h (mm per 5 min × 12). Pure function,
   unit-tested with a recorded file.
3. **FrameStore**: ordered timeline `{valid_time: Frame}`, one source of
   truth for the UI; drops frames older than 3 h; persists the last
   download in `$XDG_CACHE_HOME` so the app opens instantly.
4. **Colorizer**: mm/h → RGBA lookup table (precomputed 256-entry LUT on
   a quantised value, transparent below 0.1 mm/h). Produces one
   `Gdk.MemoryTexture` per frame at native grid size (1200×1100), done
   once per frame, not per draw.
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

# Point nowcast (M3)

The same FrameStore gives the value series at the user's cell (nearest
grid cell of the location, inverse projection) → bar chart of 25 values
and a sentence: "Rain from 14:20, heavy around 14:35" / "No rain
expected in the next 2 hours". No extra download.

# Memory and bandwidth budget

- 37 frames (−60 … +120 min) × 1200×1100 cells: as `float32` or as
  RGBA textures ≈ 195 MB each way, too much for a phone. Keep frames as
  the raw `uint16` values + gain/offset (≈ 98 MB, less if cropped to the
  visible area) and colourise lazily around the current time position
  with a small LRU of textures (e.g. 8). Measure in M2.
- Bandwidth: size of `composite_rv_LATEST.tar` every 5 min while the
  app is visible; poll only while the window is visible and on demand
  after resume. Measure in M0.

# Fallback

If decoding RV turns out impractical (see the
[radar source decision](decisions/radar-source.md)), RadarSource can be
replaced by a WMS source that downloads pre-rendered PNGs per `TIME`
for the visible bounding box in `EPSG:3857`; the rest of the pipeline
(FrameStore, RadarLayer, TimeBar) stays unchanged, only Decoder and
Colorizer are skipped.
