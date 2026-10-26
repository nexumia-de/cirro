---
type: Decision Record
title: Smooth radar playback by crossfading
description: Playback interpolates between the 5-min radar frames with a GPU crossfade at up to 30 updates per second, driven by the frame clock; speed is a menu setting.
tags: [decision, radar, animation, performance]
generated: { by: claude-code/2.1.310, at: 2026-10-26T07:00:00Z }
---

# Status

Accepted (2026-10-26, issue #12).

# Context

Playback stepped to the next 5-min frame every 400 ms, about 2.5
pictures per second, which looks jerky
([issue #12](https://github.com/nexumia-de/cirro/issues/12) asks for
30 or 60 fps and a speed setting). The radar has only one frame per
5 minutes, so anything in between has to be made up. The app has to
stay viable on an aarch64 phone: colouring a frame takes 43–63 ms on
x86_64, and only 8 textures fit in the memory budget
([radar architecture](../radar-architecture.md)).

# Options

1. **Crossfade** between the two textures around the playhead in a
   GSK cross-fade node. No new pixels are computed in Python; the
   renderer blends the existing textures (GPU with GL/Vulkan).
2. **Optical-flow advection** (estimate motion vectors between frames
   and warp the rain field along them). Looks like moving rain, but
   needs a motion field per frame pair (numpy on the phone CPU, or a
   shader GTK does not offer to Python) and new textures per
   displayed picture, i.e. re-colouring per tick, which the budget
   rules out.
3. **More steps per second without blending.** Stays jerky; the data
   has no more frames.

# Decision

- Crossfade (option 1). `TimeBar` moves a fractional playhead from a
  widget tick callback, so updates follow the display's frame clock
  instead of a GLib timeout; `RadarLayer` draws frame *i* faded into
  *i + 1* by the fraction.
- At most **30 updates per second**: a crossfade looks smooth at that
  rate, and it halves the drawing work against a 60 Hz display. With
  GTK's software renderer (cairo, no usable GPU) **10 per second**,
  because there every blend costs CPU (measured 0.84 core at 30/s vs.
  0.44 at 10/s in the dev container).
- Speeds "Slow", "Normal", "Fast" (0.5×, 1×, 2× of 0.4 s per 5-min
  step) as radio items in the main menu, kept in a key file in the
  config directory. The app has no GSettings schema yet; a key file
  needs no schema compilation in the source-tree runs, tests and
  screenshots. If more preferences come, move them to GSettings
  together.
- The slider knob glides with the playhead; dragging still snaps to
  whole frames and shows them without blending, so scrubbing stays as
  direct as before.

# Consequences

- The Python cost per update is about 0.4 ms (tick and snapshot); the
  rest is blending in the GSK renderer, cheap on a GPU, expensive in
  software. Phone measurements are still needed.
- Halfway through a fade both frames are drawn at half opacity, so a
  moving rain cell looks fainter and doubled for a moment instead of
  moving. Advection would fix that and stays possible later, behind
  the same `blend(index, fraction)` interface.
