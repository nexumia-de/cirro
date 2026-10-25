---
okf_version: "0.2"
---

# Cirro knowledge bundle

[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2) bundle of this app. Shared Phosh knowledge lives in
[../../phosh-toolkit/docs/index.md](../../phosh-toolkit/docs/index.md).
Change history is in [log.md](log.md).

# Plan

* [Roadmap](roadmap.md) - Milestones from the empty repository to a usable radar app and beyond.
* [Feature inventory](features.md) - WarnWetter features, their priority and how they map to Cirro.

# Design

* [Radar architecture](radar-architecture.md) - How radar frames are fetched, cached, projected and animated on the map.
* [Data sources](data-sources.md) - DWD open data products and other services the app uses, with open questions.

# Development

* [Bundled dependencies](dependencies.md) - Every module in the Flatpak with version, licence, bundled libraries and update check.
* [Release channels](release-channels.md) - Cirro from tags, Cirro (Nightly) from every push to main; the nightly build options, automated releases with changelog fragments, and the store screenshots.
* [Development environment](dev-environment.md) - Required hosts and host packages; how to run, test, screenshot and Flatpak-build the app.

# Decision records

* [Decisions](decisions/index.md) - Name, language, map widget, radar data source, colour scale, no own backend.
