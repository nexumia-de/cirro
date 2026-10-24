---
type: Decision Record
title: Python and PyGObject
description: Wetterblick is written in Python with PyGObject; numpy does the raster work.
tags: [decision, language, python]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:40:00Z }
---

# Status

Accepted (2026-10-24) in M0: the scaffold runs on the host (Python
3.12) and in `org.gnome.Platform//51` (Python 3.14.8, PyGObject 3.58).

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
- numpy and h5py are not in the runtime. The manifest installs the
  official manylinux wheels for cp314 (numpy 2.5.4, h5py 3.16.0 with a
  bundled HDF5 2.0.0) per architecture, so there is no compile step.
  The installed app is 95 MB, the x86_64 bundle 16 MB (M0).
- If profiling on the phone in M2 shows Python as the bottleneck, move
  the hot path (colorizer/reprojection) into a small C or Rust
  extension rather than rewriting the app.
