---
type: Plan
title: Roadmap
description: Goals and exit criteria of the milestones M0–M6, radar first; the work items are GitHub issues in the milestones linked here.
tags: [plan, roadmap, milestones]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:46:00Z }
---

# How the plan is tracked

Work items are [issues](https://github.com/nexumia-de/cirro/issues),
grouped by [milestones](https://github.com/nexumia-de/cirro/milestones)
and `area: …` labels; issues without a milestone are the
[backlog](https://github.com/nexumia-de/cirro/issues?q=is%3Aissue+is%3Aopen+no%3Amilestone).
This file keeps only the goals; never add task checklists here. The
workflow is the toolkit's
[planning with issues and milestones](../../phosh-toolkit/docs/planning.md).

# Principle

Radar first. M0–M3 deliver the core: an animated rain radar with a
2-hour forecast and a point nowcast for the user's location. Warnings,
forecasts and notifications follow only after that works well on the
phone. Feature priorities: [feature inventory](features.md).

# M0 – Verify data and scaffold (done)

Verified the RV composite and the WMS against the live services
([data sources](data-sources.md)), accepted the
[radar source](decisions/radar-source.md) and
[map](decisions/map-libshumate.md) decisions, scaffolded the app with
metadata, Flatpak manifest, CI and tests; the app installs on the phone
from the shared repository.

# M1 – Map with a static radar frame (done)

OSM map with attribution, User-Agent and tile cache; the current RV
frame decoded, reprojected to Web Mercator, coloured and aligned
([radar architecture](radar-architecture.md)); legend
([colour scale](decisions/colour-scale.md)).

# M2 – Animated radar with forecast (core feature, done)

[Milestone M2](https://github.com/nexumia-de/cirro/milestone/1)

**Goal**: the radar animates from −60 min to +120 min, refreshes every
5 minutes, starts instantly from the disk cache and centres on the
user's location.

**Exit criteria**: memory, CPU and bandwidth measured on the phone and
recorded in [radar architecture](radar-architecture.md); the first
stable release is installed on the phone
([release channels](release-channels.md)).

Done: RadarSource, FrameStore with disk cache, TimeBar, own location
through the location portal, measurements on the phone, release 0.2.0
in the shared repository.

# M3 – Point nowcast and places

[Milestone M3](https://github.com/nexumia-de/cirro/milestone/2)

**Goal**: answer "will it rain here in the next two hours?" for the
current location, for saved places and for any point on the map.
Places are pins on the map; the selected pin is what the nowcast, and
later warnings and forecasts, are about.

**Exit criteria**: 2-hour chart and a "rain starts in N min" sentence
([point nowcast](nowcast.md));
place search (Nominatim, with its usage policy) and saved places, kept
on disk with the last own position, shown as pins on the map (own
location with its own marker) and in an `AdwNavigationSplitView`
sidebar that collapses on the phone; places can be added, renamed,
moved and deleted, get a reverse-geocoded default name, and one of them
is the default place at start.

Implemented: point nowcast, and [places](places.md) as pins with the
own location, search, tap on the map, sidebar and default place. Still
open: the `on device` checks.

# M4 – Warnings

[Milestone M4](https://github.com/nexumia-de/cirro/milestone/3)

**Goal**: official weather warnings for saved places and on the map.

**Exit criteria**: warning product chosen and recorded as a decision;
warnings per place with severity and a detail page; optional overlay.

# M5 – Forecasts

[Milestone M5](https://github.com/nexumia-de/cirro/milestone/4)

**Goal**: the usual forecast view next to the radar.

**Exit criteria**: forecast source chosen and recorded as a decision;
current conditions, hourly chart and 10-day list per place.

# M6 – Extras

[Milestone M6](https://github.com/nexumia-de/cirro/milestone/5)

**Goal**: more map layers and notifications without draining the
battery.

**Exit criteria**: further WMS layers; local notifications for warnings
and imminent rain with measured battery impact.

# Risks

- **Data format churn**: DWD changed the RV format on 2026-10-20
  without a notice we could find. Keep the decoder isolated, test it
  with recorded files and fail visibly (stale guard).
- **Phone performance**: reprojection and colouring of 37 frames on
  aarch64 in Python; mitigated by numpy vectorisation and one-time index
  tables, measured in M2.
- **Flatpak size**: h5py + numpy + HDF5 add tens of MB. Alternative:
  the WMS fallback, which needs neither.
- **OSM tile policy**: fine for personal use; switch providers if usage
  grows.
