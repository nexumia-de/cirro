---
okf_version: "0.2"
---

# Cirro knowledge bundle

[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2) bundle of this app. Shared Phosh knowledge lives in
[../../phosh-toolkit/docs/index.md](../../phosh-toolkit/docs/index.md).
Change history is in [log.md](log.md).

# Plan

* [Roadmap](roadmap.md) - Goals and exit criteria of the milestones M0–M4 and M6 (no forecast view); the work items are GitHub issues in those milestones.
* [Map layers](map-layers.md) - Every DWD GeoServer layer sorted into shown and left out; how the layer code works and the issue per layer group.
* [Feature inventory](features.md) - WarnWetter features, their priority and how they map to Cirro.

# Design

* [Radar architecture](radar-architecture.md) - How radar frames are fetched, cached, projected and animated on the map.
* [Point nowcast](nowcast.md) - Rain rate at the selected place over 3 hours, the bar chart and the "Rain starts in N min" sentence.
* [Warnings per place](warnings.md) - Official DWD warnings from the CAP status zip for the selected and every saved place: a line under the nowcast, the places list and a dialog with list and detail page.
* [Places](places.md) - Saved places and the own location as pins and in a sidebar, names and search from Nominatim, add (search, current location, on the map)/rename/delete, default place.
* [Data sources](data-sources.md) - DWD open data products and other services the app uses, with open questions.

# Development

* [Bundled dependencies](dependencies.md) - Every module in the Flatpak with version, licence, bundled libraries and update check.
* [Release channels](release-channels.md) - Cirro from tags, Cirro (Nightly) from every push to main; the nightly build options, automated releases with changelog fragments, and the store screenshots.
* [Owner checks](owner-checks.md) - What only the owner can check (phone, accounts, secrets, blocked hosts, upstream releases), one checklist per closed issue.
* [Development environment](dev-environment.md) - Required hosts and host packages; how to run, test, screenshot and Flatpak-build the app.

# Decision records

* [Decisions](decisions/index.md) - Name, language, map widget, radar data source, colour scale, no own backend, smooth playback, movable own-location pin, radar focus without a forecast view, CAP warnings; proposed: DMI radar; rejected: forecast source.
