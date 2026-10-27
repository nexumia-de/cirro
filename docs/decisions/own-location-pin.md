---
type: Decision Record
title: The own-location pin can be moved by hand
description: The user may move the own-location pin with the same actions as other pins; it then says "Set by hand" until the next real fix from the location portal overwrites it.
tags: [decision, places, location]
generated: { by: claude-code/2.1.310, at: 2026-10-26T20:00:00Z }
---

# Status

Superseded on 2026-10-27: the owner dropped moving pins altogether.
Places are added (search, current location, chosen on the map) and
deleted instead; the own location comes only from the location portal
([places](../places.md)). Accepted by the owner on 2026-10-26 (issue
#41).

# Context

The own location comes from the location portal. Sometimes there is no
fix: location is off, there is no GNSS indoors, or the portal is
refused. Sometimes the fix is wrong, for example a Wi-Fi lookup that
places the phone in the wrong town. Issue #35 asked that the user can
move the own-location pin.

# Decision

- The own-location pin offers the same move actions as every pin:
  "Move on Map" and "Move To…". It can't be deleted.
- While it is set by hand, the pin and the nowcast row say "Set by
  hand".
- The next real fix from the portal overwrites the hand-set position
  and clears the "Set by hand" state.

# Consequences

- A user without location access can still use the own pin as "home",
  but it changes as soon as the portal delivers a fix. A fixed place
  belongs in a saved place instead.
- The store keeps a `manual` flag on the own location
  ([places](../places.md)).
