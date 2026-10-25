---
type: Decision Record
title: App name Cirro
description: The app is called Cirro (id de.nexumia.Cirro) and lives in suitably/cirro; it was called Wetterblick until M1.
tags: [decision, name, app-id, repository]
generated: { by: claude-code/2.1.310, at: 2026-10-25T00:10:00Z }
---

# Status

Accepted (2026-10-25), decided by the project owner.

# Context

The app started as *Wetterblick* in `suitably/wetterblick`. The owner
chose a new name and a new repository, `suitably/cirro`
(`https://github.com/suitably/cirro`).

# Decision

- Name **Cirro**, after cirrus clouds (*cirro-* is the prefix of the
  high cloud genera, e.g. cirrostratus, which often announce rain).
- App id `de.nexumia.Cirro` (domain-based, see the toolkit decision
  [domain-based names](../../../phosh-toolkit/docs/decisions/domain-names.md)), Python package `cirro`, command
  `cirro`, User-Agent `Cirro/<version> (+https://github.com/suitably/cirro)`.
- The full history of `suitably/wetterblick` moves along; the rename is
  one commit on top of it.
- The metainfo declares `<replaces>` for `io.github.suitably.Wetterblick`,
  and the `.desktop` file keeps "Wetterblick" as a search keyword.

# Consequences

- A changed app id is a new app for Flatpak: a phone that installed
  Wetterblick keeps it without updates and has to install Cirro and
  remove Wetterblick by hand.
- `suitably/phosh-apps` lists `suitably/cirro` in `apps.txt`. Without a
  `PUBLISH_TOKEN` secret in this repository, new builds appear after the
  daily publish run.
- `de.nexumia.Wetterblick` existed only on `main` for a few hours and was
  never published, so it needs no `<replaces>` entry.
- Cache directories change (`~/.cache/cirro`, libshumate's tile cache
  is per app id), so the first start after the switch downloads tiles
  again.
