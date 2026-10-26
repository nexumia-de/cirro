---
type: Decision Record
title: Own-location pin can be moved by hand
description: The user may move the own-location pin by hand; it says "Set by hand" until the next real fix from the location portal overwrites it.
tags: [decision, places, location, map]
generated: { by: claude-code/2.1.310, at: 2026-10-26T16:30:00Z }
---

# Status

Accepted by the owner (2026-10-26, issue #41, part of #35).

# Context

The own location is a pin of its own on the map (#35). It keeps the
last fix on disk and uses it when the location portal gives no new fix.
The question was whether the user may move this pin (for example with
GNSS off or indoors), or whether only the portal changes it.

# Decision

The user can move the own-location pin with the same move actions as
other pins (#39). While the position is set by hand, the pin says "Set
by hand", so a manual position never passes for a live one. The next
real fix from the portal overwrites the manual position.

# Consequences

- The place store (#36) keeps a "manual" flag next to the last position.
- The own-location pin can't be deleted or renamed away from its role;
  only its position changes.
