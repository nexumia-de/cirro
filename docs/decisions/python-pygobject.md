---
type: Decision Record
title: Python and PyGObject
description: Wetterblick is written in Python with PyGObject; numpy does the raster work.
tags: [decision, language, python]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Status

Proposed (2026-10-24). Confirm in M0 of the [roadmap](../roadmap.md).

# Context

The toolkit supports Python, Vala and Rust (`setup.sh`). The app is
mostly UI plus array work on 1200×1100 radar grids. Fast iteration
matters more than raw speed; the heavy parts (decoding, colouring,
reprojection) are vectorisable.

# Decision

Python 3 with PyGObject (GTK 4, libadwaita, libshumate, libsoup 3),
numpy for raster maths, h5py for HDF5. Build with meson, tests with
pytest. The toolkit's demo app uses the same stack.

# Consequences

- No compile step; quick changes and screenshots.
- numpy and h5py must be built into the Flatpak (size, build time).
- If profiling on the phone in M2 shows Python as the bottleneck, move
  the hot path (colorizer/reprojection) into a small C or Rust
  extension rather than rewriting the app.
