---
type: Playbook
title: Development environment
description: Network hosts, host packages, and how to run, test, screenshot and Flatpak-build Wetterblick.
tags: [development, network, cloud, testing]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:40:00Z }
---

# Required hosts

The app and its development need outbound HTTPS to:

| Host | Used for |
|---|---|
| `opendata.dwd.de` | RV radar composite, warnings, MOSMIX |
| `maps.dwd.de` | DWD GeoServer WMS (fallback radar, extra layers) |
| `www.dwd.de` | DWD product documentation |
| `api.brightsky.dev`, `brightsky.dev` | Bright Sky API and docs |
| `tile.openstreetmap.org` | Base map tiles |
| `nominatim.openstreetmap.org` | Place search (M3) |

Plus the toolkit's needs (Flathub, apt, GitHub). In a cloud agent
environment these go under the environment's network access settings
(allowed domains). On 2026-10-24 the default policy first blocked all
DWD, Bright Sky and OSM hosts (proxy answered `403` to `CONNECT`); after
they were allowed, `opendata.dwd.de`, `maps.dwd.de`, `api.brightsky.dev`
and `tile.openstreetmap.org` answered normally (21:15 UTC). Building the
Flatpak also needs `download.gnome.org`, `github.com` (protobuf-c) and
`files.pythonhosted.org` (wheels).

# Working without the network

- Keep recorded sample data in `tests/data/` (one real
  `composite_rv_*.tar`, trimmed if large, plus WMS capabilities) once it
  has been downloaded, so parsing and rendering tests run offline.
- Never replace missing live data with invented sample files: tests
  must use real recorded responses.

# Host packages

On top of `../phosh-toolkit/setup.sh` (Ubuntu 24.04):

```sh
sudo apt-get install --no-install-recommends \
  python3-h5py python3-numpy python3-pytest gir1.2-shumate-1.0 \
  hdf5-tools python3-pyproj
```

`hdf5-tools` (`h5dump`) and `python3-pyproj` are only needed to inspect
radar files. `python3-gi` is built for `/usr/bin/python3.12`; if
`python3` is another version, call `python3.12` explicitly.

# Run, test, screenshot

```sh
python3.12 -m wetterblick                 # from the source tree
python3.12 -m pytest                      # tests/ (pyproject.toml)
../phosh-toolkit/scripts/screenshot.sh -o shot.png -- python3.12 -m wetterblick
../phosh-toolkit/scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- python3.12 -m wetterblick
```

Run from the source tree, the app adds `data/icons` to the icon theme
search path, because the icon is not installed.

# Flatpak

```sh
flatpak-builder --user --install-deps-from=flathub --disable-rofiles-fuse \
  --force-clean --repo=repo build-dir io.github.suitably.Wetterblick.yml
```

Inside the build directory without installing:

```sh
flatpak build build-dir python3 -c 'import gi; gi.require_version("Shumate", "1.0")'
```

Screenshot of the sandboxed app under Broadway: Broadway's socket lives
in `~/.cache` when `XDG_RUNTIME_DIR` is unset, so share it and pass the
display through:

```sh
../phosh-toolkit/scripts/screenshot.sh -o fp.png -- sh -c 'exec flatpak build \
  --share=ipc --filesystem=/root/.cache --env=XDG_RUNTIME_DIR=/root/.cache \
  --env=GDK_BACKEND=broadway --env=BROADWAY_DISPLAY="$BROADWAY_DISPLAY" \
  build-dir wetterblick'
```

`--share=network` in the manifest is needed for radar data and map
tiles; no other permission beyond the toolkit defaults is used yet.
