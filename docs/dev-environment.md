---
type: Playbook
title: Development environment
description: Network hosts the development environment must reach and how to work when they are blocked.
tags: [development, network, cloud, testing]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Required hosts

The app and its development need outbound HTTPS to:

| Host | Used for |
|---|---|
| `opendata.dwd.de` | RV radar composite, warnings, MOSMIX |
| `maps.dwd.de` | DWD GeoServer WMS (fallback radar, extra layers) |
| `www.dwd.de` | DWD product documentation |
| `api.brightsky.dev`, `brightsky.dev` | Bright Sky API and docs |
| `tile.openstreetmap.org` | Base map tiles |
| `nominatim.openstreetmap.org` | Place search (M3) |

Plus the toolkit's needs (Flathub, apt, GitHub). In a cloud agent
environment these go under the environment's network access settings
(allowed domains). On 2026-10-24 the default policy blocked all DWD,
Bright Sky and OSM hosts (proxy answered `403` to `CONNECT`).

# Working without the network

- Keep recorded sample data in `tests/data/` (one real
  `composite_rv_*.tar`, trimmed if large, plus WMS capabilities) once it
  has been downloaded, so parsing and rendering tests run offline.
- Never replace missing live data with invented sample files: tests
  must use real recorded responses.
