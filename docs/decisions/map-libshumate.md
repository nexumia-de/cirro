---
type: Decision Record
title: libshumate as map widget
description: The map is a libshumate view with OSM raster tiles and a custom layer that draws the radar texture.
tags: [decision, map, libshumate, osm]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:40:00Z }
---

# Status

Accepted (2026-10-24); M0 confirmed it builds in the Flatpak.

# Context

The radar needs a pannable, pinch-zoomable map in GTK 4. libshumate is
the GTK 4 map library used by GNOME Maps, with touch gestures, raster
tile sources, a tile cache and custom layers. Embedding a web view
(Leaflet/OpenLayers) would pull WebKitGTK into the Flatpak and feel
non-native.

# Decision

Use `Shumate.SimpleMap`/`Shumate.Map` with an OSM raster
`Shumate.RasterRenderer`, and draw the radar in an own `Shumate.Layer`
subclass (see [radar architecture](../radar-architecture.md)).

# Consequences

- Native touch handling and theming.
- `org.gnome.Platform//51` does not ship libshumate (checked in M0).
  The manifest builds libshumate 1.7.0 (meson, `--libdir=lib` so the
  typelib lands on the default path) and its dependency protobuf-c
  1.5.2 (`--disable-protoc`); json-glib, sqlite and libsoup 3 come from
  the runtime.
- The radar texture must be projected to Web Mercator by the app.
