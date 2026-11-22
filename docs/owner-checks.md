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

# #33 Main thread cost while playing (on device)

`CIRRO_FPS` lets the update rate change without a build
([radar architecture](radar-architecture.md), measurements). Not
measured by an agent: the dev container has no Vulkan renderer.

- [ ] On the phone, play at Normal for 60 s with `CIRRO_DEBUG=1 flatpak run --env=CIRRO_FPS=30 de.nexumia.Cirro` and again with `CIRRO_FPS=20`; note the main thread's CPU (per-thread `/proc/<pid>/task/*/stat`, as on 2026-10-26) and whether 20 looks as smooth.
- [ ] Record both in the "Phone" table of [radar architecture](radar-architecture.md); if 20 is as smooth and clearly cheaper, ask an agent to set `timebar.FPS = 20`.

# #25 Notifications (on device)

Built and checked in the dev container with a stubbed background
portal and notification call ([notifications](notifications.md)).

- [ ] On the phone, turn on Preferences → Notifications: the portal asks; allow it. Close the app: it keeps running (`flatpak ps`).
- [ ] Log out and in: `cirro --background` runs without a window.
- [ ] Wait for a level-2 warning or rain at the default place: a notification shows; tapping it opens the app.
- [ ] Battery: with notifications on and the app closed, compare the battery drain over a few hours with notifications off; record it in [notifications](notifications.md).

# #43 Required check "lint" (repository settings)

- [ ] Re-import `.github/rulesets/main.json` in the repository's rulesets, so the new `lint` job is a required check.

# #51 Long press on the map (on device)

Checked with the right click's code path under Broadway and a driver
script ([places](places.md)).

- [ ] On the phone, long-press an empty spot of the map: the menu opens there; "Add Place Here" adds a named place, "Show Rain Here" shows the nowcast for that spot. A short tap and panning still only move the map.
