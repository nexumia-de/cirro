---
type: Decision Record
title: No own backend
description: Wetterblick calls DWD open data and other public services directly from the phone.
tags: [decision, architecture, backend]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:45:00Z }
---

# Status

Accepted (2026-10-24).

# Context

WarnWetter uses DWD's own backend and push service. A self-hosted
backend would add operations work for a personal app.

# Decision

No server component. All data is fetched by the app from public
services; notifications, if added (M6), are computed locally.

# Consequences

- Features that need a server (crowd reports, server push) are out of
  scope ([feature inventory](../features.md)).
- Every client request must respect the services' usage policies
  (User-Agent, caching, polling only while visible).
