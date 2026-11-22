---
type: Decision Record
title: Poll less often on metered connections
description: Accepted - on a metered connection the radar polls the analysis 15 min later and warnings every 30 min; a "Save Mobile Data" switch, on by default, turns it off.
tags: [decision, radar, bandwidth, metered, preferences]
generated: { by: claude-code/2.1.310, at: 2026-11-22T05:20:00Z }
---

# Status

Accepted (2026-11-22), issue
[#34](https://github.com/nexumia-de/cirro/issues/34), decided by best
practice on the owner's standing instruction.

# Context

Every 5-min poll fetches a new tar: 16.9 MB/h measured in light rain,
up to ~140 MB/h estimated in wide rain
([radar architecture](../radar-architecture.md)). GNOME's
`Gio.NetworkMonitor:network-metered` says when the connection is
metered (mobile data, or a hotspot NetworkManager marks as metered).

# Decision

- Metered and "Save Mobile Data" on: the radar waits for the analysis
  15 min after the newest one (4 tars an hour instead of 12) and
  retries every 5 min instead of every minute when it is late; the
  warnings poll every 30 min instead of 10. About 40 % of the full
  bandwidth; the forecast is at most 15 min older, which still leaves
  105 of the 120 forecast minutes.
- Not metered, or the switch off: unchanged (5 min, warnings 10 min).
  Leaving a metered connection polls at the normal rate at once.
- Reload (Ctrl+R) always fetches at once.
- The switch "Save Mobile Data" in the preferences (Radar group), on by
  default, kept in `settings.ini` (`[network] save-mobile-data`). One
  switch rather than a choice of intervals: GNOME apps keep such
  settings few, and 15 min is the largest step that keeps the 2-hour
  forecast useful.

# Options not taken

- On demand only (no polling while metered): the nowcast would silently
  age; rejected.
- 10 min: saves only half as much; 30 min: a quarter of the forecast
  window gone; both rejected.
