---
type: Decision Record
title: RV nowcast composite as radar source
description: Radar frames come from DWD's RV open-data composite (HDF5); the DWD GeoServer WMS is the fallback.
tags: [decision, radar, dwd, data]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Status

Proposed (2026-10-24). Confirm or revise after the M0 data checks.

# Context

Options for the radar with a 2-hour forecast (details in
[data sources](../data-sources.md)):

1. **RV composite (HDF5)** from DWD open data: raw values, 1 km, 25
   frames 0–120 min every 5 min. Needs decoding, colouring and
   reprojection in the app.
2. **DWD GeoServer WMS**: pre-rendered images with a `TIME` dimension.
   Simple, small downloads at screen resolution, but no values, DWD's
   colours only, and a new request per pan/zoom and frame.
3. **Bright Sky API**: JSON around a point. Good for point values, not
   meant for whole-Germany maps; third-party service.

# Decision

Use (1) as the primary source: the same data drives the map and the
point nowcast (M3), it works offline once downloaded, panning and
zooming need no new requests, and colours are under our control. Keep
the pipeline split so (2) can replace the download/decoder stage if (1)
proves too heavy on the phone. (3) is only a debugging aid.

# Consequences

- Dependency on h5py/numpy and the exact HDF5 layout, which DWD changed
  on 2026-10-20; the decoder must be isolated and tested with recorded
  files.
- Bandwidth: one tar every 5 min while visible (size measured in M0).
