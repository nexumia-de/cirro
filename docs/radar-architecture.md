---
type: Concept
title: Radar architecture
description: How Cirro fetches, decodes, caches, projects and animates RV nowcast frames on a libshumate map.
tags: [radar, architecture, nowcast, map, animation, location]
sources:
  - id: geoclue-locator
    resource: https://gitlab.freedesktop.org/geoclue/geoclue/-/blob/master/src/gclue-locator.c
    title: GeoClue gclue-locator.c (source selection by accuracy level)
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:30:00Z }
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

1. **RadarSource** (background thread):
   - Polls the 512-byte first tar header of `composite_rv_LATEST.tar`
     with `If-None-Match` (`304` while unchanged); a new analysis *t0*
     then costs one GET of the immutable `composite_rv_<t0>.tar` → 25
     frames, leads +0 … +120 min.
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
3. **FrameStore**: ordered timeline `{valid_time: Entry}`, one source
   of truth for the UI. Keeps each frame as its compressed HDF5 member
   and decodes it only to draw it; persists the members in
   `$XDG_CACHE_HOME/cirro/frames` so the app opens instantly; drops a
   cache older than 3 h.
4. **Colorizer**: raw value → RGBA lookup table (65 536 entries,
   transparent below 0.1 mm/h). Produces one `Gdk.MemoryTexture` per
   frame in the reprojected grid (step 5), in a worker thread ahead of
   the time bar, kept in a small LRU, not per draw.
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
7. **TimeBar**: `Gtk.Scale` with a mark per full hour and a "Now"
   mark, the measured part filled, play/pause button, label "14:05" plus
   "35 min ago" / "Now" / "Forecast +35 min"; playback via
   `GLib.timeout_add(400 ms)`, waits for frames that are not rendered
   yet, holds the last frame for three steps and loops.

# Implementation status

M1 showed one static frame, the newest analysis (`_000`). Its modules:

| Module | Step |
|---|---|
| `cirro/source.py` | Download: `Range: bytes=0-511` on `composite_rv_LATEST.tar` gives the first member's name and size; the member itself is then fetched from the timestamped tar named in it (immutable, so LATEST being replaced between the two requests does no harm). Falls back to slicing if a server ignores ranges. M2: see below. |
| `cirro/radar.py` | Decoder → `Frame` (`uint16` raw, gain/offset, times, forecast flag) and `Grid` (projdef, size, outer edges from the `UL` corner). |
| `cirro/projection.py` | Polar stereographic forward/inverse and Web Mercator in numpy (pyproj is not in the Flatpak); agrees with pyproj to < 1 mm. `reproject_grid()` builds the index table for a 1400-px-wide Mercator image (1400×1364, ≈ 1.2 km per pixel), cached per `Grid`. |
| `cirro/colors.py` | 65 536-entry RGBA lookup table on the raw value ([colour scale](decisions/colour-scale.md)). |
| `cirro/radar_layer.py` | `RadarLayer` computes the texture rectangle with `MapSource.get_x/get_y` like `shumate_viewport_location_to_widget_coords()` and applies the map rotation to the snapshot. Linear filtering below zoom 9, nearest from zoom 9. |

M2 animates the whole timeline:

| Module | Step |
|---|---|
| `cirro/source.py` | `poll_latest()` (conditional range request, `304` → nothing new), `fetch_tar()` (whole timestamped tar), `fetch_analysis()` (a past `_000` member by two range requests), and the refresh policy `next_poll()` / `is_stale()`. |
| `cirro/frames.py` | `FrameStore`: entries keyed by valid time, newer analysis wins; `timeline()` = analyses from −60 min to *t0* plus *t0*'s forecasts; `missing_past()`; disk cache with atomic writes; `radar.peek()` reads the times from the HDF5 attributes in 5 ms without decompressing the data. |
| `cirro/radar_source.py` | `RadarSource` (GObject): loads the cache, then polls in a worker thread; fetches missing past analyses newest first (a `404` is remembered, other errors abort the round); signals `changed` and `failed`; `stale` property. |
| `cirro/renderer.py` | `FrameRenderer`: worker thread that decodes, reprojects and colours the requested frames (selected one first) into an LRU of 8 textures. |
| `cirro/timebar.py` | `TimeBar` widget (step 7). |
| `cirro/location.py` | Own location through the location portal (below). |
| `cirro/window.py` | Map, location button and marker, stale banner, time bar, legend. Polls, plays and tracks the location only while the window is mapped and not `suspended`. |

## Refresh policy

A new analysis appears 3–4 min after its nominal time, so the next poll
is due at *t0* + 9 min. When it is late, RadarSource retries every
minute for 10 min, then every 5 min. Failed background polls are only
logged; the stale guard shows an `AdwBanner` "Radar data from 14:05 is
out of date" with "Reload" once *t0* is more than 30 min old. A failed
manual reload, or a failure with no data at all, shows a toast with
"Retry". Polls pause while the window is hidden and catch up when it
comes back.

Timings on the x86_64 dev container (M1): index table 0.5 s (once),
colouring 40 ms per frame, member download 0.1–0.6 MB.

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

# Own location

`cirro/location.py` uses libportal (`Xdp`, `XdpGtk4`, both in
`org.gnome.Platform//51`) to start the location portal's monitor on
the first tap of "Show My Location"; the portal asks the user and
GeoClue provides the fix, so the manifest needs no permission. The map
then animates to the fix at zoom ≥ 8.5 and shows a `Shumate.Point`.
Updates arrive for moves of 200 m or more; the monitor stops while the
window is hidden. Accuracy is `EXACT`: GeoClue starts a source only if
the requested level is at least the level the source offers, and its
modem GPS (and NMEA) sources offer `EXACT`, so any coarser request
leaves the phone's GNSS off and relies on Wi-Fi/cell lookups alone
(checked in GeoClue's `gclue-locator.c` and `gclue-modem-gps.c`,
2026-10-25).[^geoclue-locator] Without a portal
(e.g. the dev container) the button shows the toast "Location
unavailable". Not yet tried on the phone.

# Point nowcast (M3)

The same FrameStore gives the value series at the user's cell (nearest
grid cell of the location, inverse projection) → bar chart of 25 values
and a sentence: "Rain from 14:20, heavy around 14:35" / "No rain
expected in the next 2 hours". No extra download.

# Memory and bandwidth budget

- 37 frames (−60 … +120 min) × 1200×1100 cells: as `float32` or as
  RGBA textures (1400×1364 px, 7.6 MB each) ≈ 195–280 MB, too much for
  a phone; even decoded `uint16` would be ≈ 98 MB. The FrameStore
  therefore keeps the compressed members (≈ 0.47 MB each in wide rain,
  17 MB for 37) and the renderer keeps 8 textures (61 MB). Decoding again
  costs 12–35 ms per frame.
- `reproject_grid()` builds the index table in blocks of 128 rows: the
  peak RSS of building it dropped from 210 MB to 112 MB, and it got
  faster (0.72 s → 0.20 s).
- Bandwidth: a new analysis costs one tar of 1.9–11.6 MB, i.e. up to
  ~140 MB per hour while the window is visible in wide rain; a poll
  without news costs one `304`. A start with an empty cache adds 12 past
  members (≈ 6 MB in wide rain); with a warm cache only the frames that
  became past since are fetched (none if the app ran within the hour).
  If this is too much on mobile data, poll less often on a metered
  connection (`Gio.NetworkMonitor:network-metered`).

## Measurements

x86_64 dev container, 4 cores, Python 3.12, 2026-10-25 around 12:00 UTC
(wide rain, 11.5 MB tar):

| What | Value |
|---|---|
| Baseline after importing GTK, libadwaita, numpy, h5py | 65 MB RSS |
| FrameStore with 37 frames | +19 MB |
| Decode one member / reproject + colour | 12–35 ms / 43–63 ms |
| Whole app while playing (Broadway, 8 textures) | ≈ 245 MB RSS, ≈ 0.3 core |
| First start, empty cache | 17.3 MB downloaded |

Phone numbers are still missing. To collect them, run
`CIRRO_DEBUG=1 flatpak run de.nexumia.Cirro`: it logs every download
(status, bytes, seconds), the decode and colour time of every frame,
and after every refresh the frame count, total bytes received, RSS and
CPU time. Then tune `renderer.CAPACITY` (memory vs. CPU while playing:
with fewer textures than frames, every loop renders each frame again)
and the poll interval.

# Fallback

If decoding RV turns out impractical (see the
[radar source decision](decisions/radar-source.md)), RadarSource can be
replaced by a WMS source that downloads pre-rendered PNGs per `TIME`
for the visible bounding box in `EPSG:3857`; the rest of the pipeline
(FrameStore, RadarLayer, TimeBar) stays unchanged, only Decoder and
Colorizer are skipped.

[^geoclue-locator]: GeoClue gclue-locator.c
