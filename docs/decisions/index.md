# Decision records

* [App name Cirro](app-name.md) - Renamed from Wetterblick; new app id and repository suitably/cirro.
* [Python and PyGObject](python-pygobject.md) - The app is written in Python with PyGObject, numpy for raster work.
* [libshumate as map widget](map-libshumate.md) - The map is a libshumate view with OSM raster tiles and an own radar layer.
* [RV nowcast composite as radar source](radar-source.md) - Radar frames come from DWD's RV open-data composite, WMS is the fallback.
* [No own backend](no-backend.md) - The app calls public services directly.
* [Radar colour scale](colour-scale.md) - Eight mm/h classes from 0.1 to 50, blue to magenta, semi-transparent.
* [AGPL-3.0 license](license.md) - Strong copyleft keeps every copy open; contributor terms keep the author's rights.
* [Smooth radar playback](smooth-playback.md) - Crossfade between frames at up to 30 updates per second on the frame clock; Slow/Normal/Fast in the menu.
* [CAP open data as warning source](warning-product.md) - Proposed: warnings per place from DWD's CAP status files; WMS layer only for the optional overlay.
* [MOSMIX directly as forecast source](forecast-source.md) - Proposed: forecasts from MOSMIX_L single-station KMZ files, not Bright Sky.
* [DMI as second radar source for Denmark](dmi-radar.md) - Proposed: DMI composite behind a radar provider interface after M3, past frames only; not verified live.
