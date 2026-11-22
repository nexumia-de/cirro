---
type: Playbook
title: Owner checks
description: Checks only the owner can do (on the phone, with an account, a secret, a blocked host or an upstream release), one short checklist per closed issue.
tags: [owner, device, checklist]
generated: { by: claude-code/2.1.310, at: 2026-11-22T12:00:00Z }
---

# How to use this file

Agents close an issue when everything that works without the phone, an
account, a secret or an upstream project is done, and put what is left
here. Nothing in this file has been run by an agent. Tick a box when
you have done it, note the result in the linked concept file, and
delete a section once all its boxes are ticked. If a check fails, open
an issue.

# #50 Places view: back to the map (on device)

Built in 47da5f1 ([places](places.md)); keyboard path checked under
Xvfb only.

- [ ] On the phone, open the places list and swipe right to left: the map shows again, nothing else changes.
- [ ] Tap the "Back to Map" button (›) in the list's header: same result.

# #45 Nominatim usage policy (blocked host)

The OSMF pages could not be reached from the cloud container or a web
fetch (2026-10-26, 2026-11-22); [data sources](data-sources.md)
section 9 lists what the code does.

- [ ] Read https://operations.osmfoundation.org/policies/nominatim/ and compare it with section 9 (1 request/s, identifying User-Agent, caching, no autocomplete, no bulk queries, ODbL attribution).
- [ ] Read https://osmfoundation.org/wiki/Licence/Attribution_Guidelines and check the search dialog note ("Place names © OpenStreetMap contributors (ODbL)") and the About dialog credit.
- [ ] Mark section 9 *(live)* with the date, or open an issue for what differs.

# #21 Warnings per place (on device)

Built and checked under Broadway with live warnings ([warnings](warnings.md)).

- [ ] On the phone, select a place with a warning: the line under the nowcast shows it; tap it, open a warning, swipe back.
- [ ] With `CIRRO_DEBUG=1` on a stormy day, note how much the warnings download per hour and record it in [warnings](warnings.md).

# #34 Poll less often on a metered connection (on device)

Built with tests on a fake network monitor ([decision](decisions/metered-polling.md)).

- [ ] On the phone on mobile data, run `CIRRO_DEBUG=1 flatpak run de.nexumia.Cirro` for 30 min: the log shows a radar download about every 15 min; note the MB/h in [radar architecture](radar-architecture.md).
