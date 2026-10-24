---
type: Decision Record
title: Radar colour scale
description: Eight rain-rate classes from 0.1 to 50 mm/h, blue to magenta, semi-transparent over the map.
tags: [decision, radar, colours, legend]
generated: { by: claude-code/2.1.310, at: 2026-10-24T23:50:00Z }
---

# Status

Accepted (2026-10-24, M1).

# Context

The RV composite gives precipitation per 5 minutes; readers think in
rain rate (mm/h). The overlay sits on a busy OSM map and must stay
readable on a small phone screen in daylight. DWD's own colour tables
are part of its branding, which the app must not copy (see
[AGENTS.md](../../AGENTS.md)).

# Decision

- Show rain rate in mm/h (mm per 5 min × 12).
- Eight classes with lower bounds 0.1, 0.5, 1, 2, 5, 10, 20, 50 mm/h,
  coloured light blue → blue → green → yellow → orange → red → magenta
  (`wetterblick/colors.py`). Below 0.1 mm/h and outside the radar
  coverage the overlay is transparent.
- One alpha value (`0xb8`) for all classes, so the base map stays
  visible underneath.
- A legend bar below the map shows each class with its lower bound.

# Consequences

- Colouring is one 65 536-entry lookup table per gain/offset pair, so a
  frame is coloured in about 40 ms on x86_64.
- Areas outside the coverage look the same as dry areas. Telling them
  apart (e.g. a faint hatch) is left for later.
