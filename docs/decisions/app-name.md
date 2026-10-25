---
type: Decision Record
title: App name Cirro
description: The app is called Cirro (id io.github.suitably.Cirro) and lives in suitably/cirro; it was called Wetterblick until M1.
tags: [decision, name, app-id, repository]
generated: { by: claude-code/2.1.310, at: 2026-10-25T00:10:00Z }
---

# Status

Accepted (2026-10-25), decided by the project owner.

# Context

The app started as *Wetterblick* in `suitably/wetterblick`. The owner
chose a new name and a new repository, `suitably/cirro`
(`https://github.com/suitably/Cirro.git`).

# Decision

- Name **Cirro**, after cirrus clouds (*cirro-* is the prefix of the
  high cloud genera, e.g. cirrostratus, which often announce rain).
- App id `io.github.suitably.Cirro`, Python package `cirro`, command
  `cirro`, User-Agent `Cirro/<version> (+https://github.com/suitably/cirro)`.
- The full history of `suitably/wetterblick` moves along; the rename is
  one commit on top of it.
- The metainfo declares `<replaces>` for `io.github.suitably.Wetterblick`,
  and the `.desktop` file keeps "Wetterblick" as a search keyword.

# Consequences

- A changed app id is a new app for Flatpak: a phone that installed
  Wetterblick keeps it without updates and has to install Cirro and
  remove Wetterblick by hand.
- `suitably/phosh-apps` must list `suitably/cirro` instead of
  `suitably/wetterblick` in `apps.txt` once Cirro has published its
  first `latest` release; the new repository needs the `PUBLISH_TOKEN`
  secret for that.
- Cache directories change (`~/.cache/cirro`, libshumate's tile cache
  is per app id), so the first start after the switch downloads tiles
  again.
