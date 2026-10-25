---
type: Decision Record
title: AGPL-3.0 license
description: Cirro is licensed under AGPL-3.0-or-later; contributor terms keep the author free to relicense.
tags: [decision, license, legal]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:10:00Z }
sources:
  - id: agpl
    resource: https://www.gnu.org/licenses/agpl-3.0.html
    title: GNU Affero General Public License v3.0
  - id: osd
    resource: https://opensource.org/osd
    title: The Open Source Definition
---

# Status

Accepted (2026-10-24) by the owner. Requirements: the owner stays free
to do anything with the app; others should not be able to commercialise
it.

# Context

- No open-source license can forbid commercial use: the Open Source
  Definition requires "no discrimination against fields of
  endeavor".[^osd] A noncommercial license (PolyForm Noncommercial
  1.0.0) was considered and rejected: the app would not be open source,
  distributions would not package it and Flathub would label it
  proprietary.
- A license only binds others. As copyright holder the owner can always
  use, sell or relicense their own code.

# Decision

License the code under the GNU Affero General Public License v3.0 or
later (`AGPL-3.0-or-later`, `LICENSE`).[^agpl] Anyone who distributes
the app or a modified version, or runs a modified version as a network
service, must publish the complete corresponding source under the same
license. This makes closed commercial copies impossible, though open
commercial redistribution stays legal.

Contributions are accepted only under the terms in `CONTRIBUTING.md`,
which give the owner an unrestricted license to them, so the owner can
still relicense the whole app later.

# Consequences

- Metainfo `project_license` and `metadata_license` (CC0-1.0 for the
  metainfo itself) as SPDX ids; Flathub and distributions accept the
  app as free software.
- GPL-3.0 code (such as phosh-toolkit's examples) may be reused here:
  GPL-3.0 and AGPL-3.0 are compatible (AGPL section 13).
- Third-party data and libraries keep their own terms: DWD open data
  and OSM (ODbL) require attribution in the app; GTK, libadwaita,
  libshumate (LGPL), numpy and h5py (BSD) are compatible.

[^agpl]: GNU Affero General Public License v3.0
[^osd]: The Open Source Definition
