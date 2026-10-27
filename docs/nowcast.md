---
type: Concept
title: Point nowcast
description: Rain rate at the selected place from −60 to +120 min, the 2-hour bar chart below the map and the "Rain starts in N min" sentence.
tags: [radar, nowcast, chart, location]
generated: { by: claude-code/2.1.310, at: 2026-10-26T10:00:00Z }
---

# What it shows

Below the map, above the time bar: one sentence about rain at the
selected place, what the place is ("My location", "Set by hand", "Not
saved"), its actions menu, and a bar chart with one bar per 5-min frame
from −60 min to +120 min. The place is the selected pin, a tapped point
or a search result ([places](places.md)); its name is the header title.
Without any, the row reads "Tap the map or search for a place" and the
chart is hidden. No extra download: the
values come from the [FrameStore](radar-architecture.md) frames the map
animates.

# Value series

`cirro/nowcast.py` (no GTK) turns the timeline into `Value`s (valid
time, minutes relative to the analysis time *t0*, forecast flag, rate
in mm/h, NaN outside the coverage). `radar.sample()` reads the rate of
the grid cell containing the point (`radar.cell()`, the forward
stereographic projection) without building the float array of the
whole frame; HDF5 still decompresses the member, which is one chunk.
37 members cost 0.23–0.33 s on the x86_64 dev container (recorded
19:40 UTC analysis, 2026-10-26), against about 2 s for full decodes.
Values are cached per member and point, so a new analysis only samples
its 25 new members; the worker thread drops a computation when the
place or the timeline changed in the meantime.

# Sentence

Thresholds:

- **Rain** is a rate of at least 0.1 mm/h, the lowest class of the
  [colour scale](decisions/colour-scale.md): what the map shows as rain
  is what the sentence calls rain.
- Rain **stops** when it stays dry for 2 frames (10 min) or until the
  end of the forecast, so one dry frame inside a shower is no stop.
  Rain **starts** at the first frame with rain, to warn early.
- N is the lead of that frame relative to *t0*, the time the time bar
  calls "Now", so both agree; the frame's valid time is the end of its
  5-min interval.

| Now | Later | Sentence |
|---|---|---|
| dry | rain at +35 min | Rain starts in 35 min |
| dry | dry | No rain expected in the next 2 hours |
| rain | dry from +25 min | Rain stops in 25 min |
| rain | rain throughout | Rain for the next 2 hours |
| rain / dry | no forecast frames | Raining now / No rain now |
| no data | | No radar data for this place |

Durations of an hour or more read "1 h 25 min".

# Chart

`cirro/nowcast_view.py`: `NowcastChart` is a `Gtk.Widget` drawn with
`GtkSnapshot` (`append_color`, `append_layout`), because PyGObject's
cairo draw functions need pycairo, which the dev host lacks. Bar height
is logarithmic between 0.05 and 50 mm/h (0.1 mm/h → 10 %, 1 → 43 %,
10 → 77 %), bars use the radar scale's colours (data colours), and
the guides at 1 and 10 mm/h, the axis, the "Now" line and the labels use
the widget's foreground colour, so they follow dark and high-contrast
styles. Colour is not the only carrier: bar height, the guide labels,
the legend below and the sentence carry the same information; the
chart is an accessible image whose description is the sentence. Time
labels: "Now" and every full local hour that does not collide with it.

Layout: 72 px high; fits 360 px (37 slots of about 9 px). An
`AdwBreakpoint` hides the chart below 560 sp of window height (phone in
landscape), where the map would get too small; the sentence stays.
Checked at 360×720 (light and dark), 720×360 and 1000×700 with the
recorded demo data.

# Open points

- Sampling time on the phone is not measured yet.
