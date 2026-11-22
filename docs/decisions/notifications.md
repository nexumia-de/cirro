---
type: Decision Record
title: Notifications from the background portal with point queries
description: Accepted - opt-in notifications for the default place; the app keeps running without a window via the background portal; rain from one WMS point query, warnings from the shared CAP file; warnings from level 2.
tags: [decision, notifications, background, battery, warnings, rain]
generated: { by: claude-code/2.1.310, at: 2026-11-22T05:40:00Z }
---

# Status

Accepted (2026-11-22), issue
[#25](https://github.com/nexumia-de/cirro/issues/25), decided by best
practice on the owner's standing instruction.

# Context

M6 asks for local notifications for warnings and imminent rain without
draining the battery. There is no own backend ([decision](no-backend.md)),
so the phone has to poll. A radar tar costs 2–12 MB and its decode
tens of ms per member; GNOME offers the background portal (run without
a window, autostart) and `GNotification` (notification portal in the
Flatpak).

# Decision

- **Opt-in** switch in the preferences, off by default; turning it on
  asks the background portal (with autostart). A refusal keeps it off.
- **Which place**: the default place (own location as fallback). One
  place keeps the checks cheap and the notifications meaningful; more
  places can follow if users ask.
- **Rain**: `GetFeatureInfo` of `Radar_rv_product_1x1km_ger` over the
  2-hour time range at the point, ≈ 5 KB, values equal to the RV file
  (checked live 2026-11-22, [data sources](../data-sources.md),
  section 2). Every 15 min, 30 when saving mobile data. Notify when dry
  now and rain starts within 30 min; once per shower.
- **Warnings**: the shared CAP source ([decision](warning-product.md)),
  new warnings of level 2 (Moderate) and higher; level 1 (frost, fog)
  comes nearly every winter night and would make users turn
  notifications off. Updates of a notified warning are not repeated.
- **Process**: the app holds itself while notifications are on; the
  window and the radar frames are released when it closes.

# Options not taken

- Download the tar in the background: up to 45 MB/h and a decode every
  15 min; rejected for battery and data.
- A separate D-Bus service or systemd timer: more packaging for the same
  polling; the background portal covers Flatpak and Phosh.
- Notify level 1 warnings, or a level choice: no choice until users ask.

# Consequences

- The battery impact is measured on the phone
  ([owner checks](../owner-checks.md)).
- The GeoServer point query is not in DWD's documented open data
  product list; if it changes, rain notifications stop (logged), the
  map is not affected.
