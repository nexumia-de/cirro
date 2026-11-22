---
type: Concept
title: Warnings per place
description: Official DWD warnings for the selected place and every saved place, from the CAP status zip on open data; a line under the nowcast, the places list and a dialog with list and detail page.
tags: [warnings, cap, places, dwd]
generated: { by: claude-code/2.1.310, at: 2026-11-22T05:00:00Z }
sources:
  - "[^decision]: decisions/warning-product.md"
  - "[^data]: data-sources.md, section 4"
---

# What the user sees

- Below the nowcast and the sun/wind line, a full-width button for the
  selected place: "⚠ Frost warning" or "2 warnings: Frost, fog". It is
  hidden while the place has no warning.
- In the places list, each row's subtitle starts with the same line.
- The button opens a dialog (a bottom sheet on the phone) with the
  warnings, most severe first: DWD's colour as a chip, the headline,
  "Level 1 of 4 · Minor" in words (colour is never the only carrier)
  and the period ("Now until 08:00", "From Sun 22:00 until Mon 09:00",
  "Now, until further notice"). A row pushes the detail page inside the
  dialog (back button, swipe back): headline, level, period, height
  limit when the warning applies only above or below a height, the
  description, the instruction and "Source: Deutscher Wetterdienst".
  With one warning the dialog opens on its detail page.
- Texts are DWD's English CAP texts, unchanged, so they carry the DWD
  source note.

# How it works

- `cirro/warnings/source.py`: `WarningSource` downloads
  `COMMUNEUNION_DWD_STAT/…_LATEST_…_EN.zip` with `If-None-Match` every
  10 min while the window is visible (2 min after a failure), keeps the
  zip and its `ETag` in `~/.cache/cirro/warnings/` and loads it at start,
  so warnings show offline. Demo mode (`CIRRO_DEMO_DATA`) never polls.
- `cirro/warnings/cap.py` (no GTK): parses every CAP XML of the zip
  (skips other statuses than `Actual` and cancellations), keeps the
  polygons of the "polygonal event area" areas with their
  `EXCLUDE_POLYGON` holes and the warn cell names, and finds the
  active warnings at a point by even–odd ray casting, most severe
  first, then by onset. Warnings without polygons (sea areas) never
  match a place.[^data]
- `cirro/warnings/text.py`: period, level and height texts.
- `cirro/warnings/view.py`: the button and the dialog.
- The window recomputes the warnings when the selection, the places or
  the status change.

Why CAP and not the WMS or WFS: [decision](decisions/warning-product.md).[^decision]
The map overlay stays the WMS layer of the [map layers](map-layers.md).

# Tests

`tests/test_warnings.py` uses DWD's recorded English status of
2026-11-22 04:38 UTC (`tests/data/cap/`, 50 warnings: frost, fog, icy
surfaces, two sea warnings without polygon): parsing, times with
offsets, holes, places with and without warnings, expiry, sorting,
texts and the disk cache.

# Limits

- Bandwidth: 0.2–0.8 MB per change of the status; not yet measured on
  the phone ([owner checks](owner-checks.md)).
