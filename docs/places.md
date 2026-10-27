---
type: Concept
title: Places
description: Saved places and the own location as pins on the map and in a sidebar; the selected place drives the nowcast; names from Nominatim, search, adding (search, current location, on the map), renaming, deleting and the default place.
tags: [places, map, pins, location, search, geocoding, preferences]
generated: { by: claude-code/2.1.310, at: 2026-10-26T20:00:00Z }
---

# What the user sees

Each saved place is a pin on the map, and the own location has its
own pin with a different icon. Tapping a pin selects it. The selected
pin turns blue and its name becomes the header title. The
[point nowcast](nowcast.md) below the map (sentence and chart) is for
that place. The search (magnifier in the header, Ctrl+F) shows a found
city or town without saving it: it gets a blue pin, its name becomes
the title, and the nowcast row says "Not saved" and offers "Add Place".
A tap on the map does nothing; it only pans (the owner's call on
2026-10-27: a pin dropped by every tap got in the way).

New places come from the "+" menu of the places list ("Add Place"):

- **Search…**: the search dialog; the result is saved at once.
- **Current Location**: a saved place at the own location's current
  fix. Without a fix from this session it starts the location portal
  and saves on the first fix, or shows "Location unavailable".
- **Choose on Map**: a pick mode. A fixed blue pin sits in the middle
  of the map, the header shows "Cancel" and "Save", and the user pans
  the map under the pin; "Save" adds a place at the map centre and
  selects it. Pins and rows don't change the selection meanwhile.

Places can't be moved. To change a spot, add a new place and delete
the old one.

With no place at all, the nowcast row reads "Add a place or search for
one". The old fallback to the map centre is gone (issue #38).

On the desktop the places are also listed in a sidebar. On the phone
(below 600 sp) the sidebar is its own page behind the header's back
button. That list is the keyboard and screen reader route to the places
(issue #18): selecting a row selects the same place as its pin and
centres the map on it.

# Data model (`cirro/places.py`)

There is no GTK in the model, so it is tested without a display
(`tests/test_places.py`).

- `Place` (GObject): `id`, `own`, `has_position`, `latitude`,
  `longitude`, `custom_name`, `default_name`, and the derived `title`: the custom name, else the
  default name, else the coordinates ("52.52° N, 13.40° E").
- `PlaceStore.model` is a `Gio.ListStore`. The own location is always
  item 0 and can't be deleted. The saved places follow in the user's
  order. The pins (`cirro/pins.py`) and the sidebar
  (`cirro/places_view.py`) both read from it.
- Every change is saved at once to `$XDG_DATA_HOME/cirro/places.json`
  (in the Flatpak: `~/.var/app/<app id>/data/cirro/places.json`). The
  file is first written to a `.tmp` file and then renamed
  (`os.replace`), so a crash never leaves half a file. It has a
  `version` field (1). A missing file means no places yet. An
  unreadable file or an unknown version is renamed to
  `places.json.bad` and the app starts empty. A broken entry is
  skipped.
- The file also holds the default place (`default`, an id) and
  `location_enabled`.

# Own location (issue #41)

- The last fix is stored. At startup the pin is shown at the stored
  position and labelled "My location, last known" until a new fix
  arrives. If the portal fails, the old position stays and the pin is
  not hidden.
- After the first fix, `location_enabled` is set and the portal is
  started at every launch, so the pin follows the user without a tap.
  Before that, the portal starts only on "Show My Location", as in M2.
- The own location comes only from the portal; it can't be moved by
  hand (the [decision](decisions/own-location-pin.md) that allowed it
  is superseded). A `manual` flag in files from before is ignored.
- A fix renames the own location only if it moved more than 1 km. The
  portal reports moves of 200 m or
  more, so this keeps Nominatim requests rare.

# Names (issue #37, `cirro/geocode.py`, `cirro/namer.py`)

- A new place without a name gets one from Nominatim `/reverse` at
  zoom 14: the first of city → town → village → suburb → municipality →
  county, then the object's own name. This is tested on recorded
  answers ([data sources](data-sources.md), section 9).
- Lookups happen only when a place is created, or when the
  own location moved more than 1 km. They never happen per frame or per
  pan. The result is stored as `default_name`, so the name survives
  restarts.
- One worker thread runs all lookups, and `geocode._get` allows at most
  one request per second across all threads, as the usage policy asks.
- When offline or on an error, the title shows the coordinates, and the
  lookup is retried after 5 minutes and at the next start. Where
  Nominatim knows no name (at sea), the coordinates become the default
  name, so they are not looked up again.
- A place added from a search result takes the result's name as its
  default name, so no lookup is needed; "Current Location" takes the
  own location's name.
- The ODbL attribution "Place names © OpenStreetMap contributors
  (ODbL)" is shown below the search results. The About dialog's "Map
  Data" section names Nominatim.

# Search (issue #13, `cirro/search.py`)

An `AdwDialog`: a bottom sheet on the phone and a floating dialog on the
desktop. It searches only when the user presses Enter, because the
Nominatim policy forbids search as you type. It shows up to 10 results
(name and region). Results are cached for the session. While searching
a spinner is shown; with no results, or offline, an `AdwStatusPage`
says so. The same dialog is used two ways:

- from the header: show the result as a point (not saved);
- from the sidebar's "+" menu ("Search…"): add the result as a place.

# Actions on a place (issue #39)

The selected place's actions are in a menu button next to the nowcast
sentence ("Place Actions"). Each sidebar row has the same menu, plus
"Move Up"/"Move Down".

| Action | Effect |
|---|---|
| Add Place | Only for an unsaved search result: saves it and selects it. |
| Rename… | `AdwAlertDialog` with an `AdwEntryRow` (Enter confirms). "Use Default Name" drops the custom name. |
| Set as Default | The place selected at startup. |
| Delete | Removes the place. The toast offers "Undo", with no confirmation dialog. The own location can't be deleted. |
| Move Up / Move Down | Reorder in the sidebar (keyboard friendly; no drag and drop). |

The issue asked for a bottom sheet on the phone and a popover on the
desktop. A `GtkPopoverMenu` from a menu button is used everywhere
instead: it holds a few short items, is the stock pattern, and needs no
`AdwBottomSheet` (libadwaita 1.6; the Ubuntu 24.04 dev host has 1.5).

## Why "Choose on Map" pans the map

libshumate 1.x markers can't be dragged: `ShumateMarker` has no
`draggable` property (checked by introspection of libshumate on the
dev host, 2026-10-26), and dragging a child would fight the map's own
pan gesture. Panning the map under a fixed pin works the same with
touch, mouse and keyboard.

# Default place (issue #40, `cirro/preferences.py`)

Preferences (main menu, Ctrl+,) is an `AdwPreferencesDialog` with:

- "Default Place": the own location or one saved place. At startup this
  place is selected and the map centres on it at zoom 8.5. If it was
  deleted, or has no position, the own location is used; with no own
  position either, nothing is selected.
- "Playback Speed": moved here from the main menu. The setting stays in
  `settings.ini` (`cirro/timebar.py`) through the action
  `app.playback-speed`.

"Reload Radar" moved from the header into the main menu (Ctrl+R, F5).
The header had no room for it at 360 px next to the back, location and
search buttons.

# Pins (issue #38, `cirro/pins.py`)

- The pins are `GtkButton`s in a `ShumateMarkerLayer`, styled `osd` and
  `circular`. `style.css` (`.cirro-pin`) makes them at least 44×44 px.
  The own location uses `find-location-symbolic` and saved places
  `mark-location-symbolic`, so the icon tells them apart, not colour.
  The selected pin adds `suggested-action`, and the header title names
  it, so colour is not the only cue there either.
- Each button has the place's name as tooltip and accessible label. For
  the own location the label also gives its state ("My location, last
  known"), and the selected pin's label ends in "selected". Pins can be reached with Tab. The sidebar is the list
  alternative.
- A pin outside the radar coverage reads "No radar data for this
  place", the same as any point there.
- The layer is rebuilt on every store change, which is cheap for a
  handful of places.

# Checked

Store screenshots: the "radar" and "forecast" shots show the recorded
places from `tests/data/places-demo.json`. There is no shot of the
sidebar yet: under Broadway with GTK 4.24, rows that use the same
symbolic icon lose their menu buttons in the picture (toolkit
[screenshot testing](../../phosh-toolkit/docs/screenshot-testing.md)).

At 360×720 and 1000×700 with recorded data (`CIRRO_DEMO_PLACES`):
pins, the selected pin, the sidebar, preferences, the search with
recorded results, rename, the delete toast, and the place menu; on
2026-10-27 also the "+" menu, "Choose on Map" (saved with a live
Nominatim name) and that a tap on the map adds no point. In Broadway, real clicks on the map, on a pin and on the menu
button worked (2026-10-26). On the phone the owner confirmed
(2026-10-27): with location off, the own pin shows the last position
marked as not current, and it updates once a fix arrives again. Not
checked yet: touch on the phone, the
on-screen keyboard over the rename and search dialogs, and the own
location with location off, on a cold start without GNSS and with a
late fix (`on device` items of #41).
