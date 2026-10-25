---
type: Playbook
title: Development environment
description: Network hosts, host packages, and how to run, test, screenshot and Flatpak-build Cirro.
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

Plus the toolkit's needs (Flathub, apt, GitHub). In a fresh container,
`flatpak-builder --user` needs a user remote first:
`flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`.
In a cloud agent
environment the hosts above go under the environment's network access settings
(allowed domains). On 2026-10-24 the default policy first blocked all
DWD, Bright Sky and OSM hosts (proxy answered `403` to `CONNECT`); after
they were allowed, `opendata.dwd.de`, `maps.dwd.de`, `api.brightsky.dev`
and `tile.openstreetmap.org` answered normally (21:15 UTC). Building the
Flatpak also needs `download.gnome.org`, `github.com` (protobuf-c),
`files.pythonhosted.org` (wheels) and `raw.githubusercontent.com`
(libaec licence text, see [dependencies](dependencies.md)).

Checking for updates locally with flatpak-external-data-checker (see
[dependencies](dependencies.md)) also needs `pypi.org`,
`api.github.com` and, to pull the checker's container image,
`pkg-containers.githubusercontent.com`. On 2026-10-25 the cloud proxy
refused `pkg-containers.githubusercontent.com` (`403`), and
`api.github.com` answered `403` for repositories outside the session,
so the protobuf-c check only runs in CI; the checker ran from a source
checkout instead of the image.

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

`hdf5-tools` (`h5dump`) is only needed to inspect radar files;
`python3-pyproj` also lets a test compare the projection with PROJ.
`python3-gi` is built for `/usr/bin/python3.12`; if
`python3` is another version, call `python3.12` explicitly.

# Run, test, screenshot

```sh
python3.12 -m cirro                 # from the source tree
python3.12 -m pytest                      # tests/ (pyproject.toml)
../phosh-toolkit/scripts/screenshot.sh -o shot.png -- python3.12 -m cirro
../phosh-toolkit/scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- python3.12 -m cirro
```

Run from the source tree, the app adds `data/icons` to the icon theme
search path, because the icon is not installed.

# Flatpak

```sh
flatpak-builder --user --install-deps-from=flathub --disable-rofiles-fuse \
  --force-clean --repo=repo build-dir de.nexumia.Cirro.yml
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
  build-dir cirro'
```

Two things fail only in the cloud dev container, not on a device:

- **HTTPS from Python**: the agent proxy's CA is not in the runtime's
  trust store (`/etc/pki/tls/cert.pem`), so downloads fail with
  `CERTIFICATE_VERIFY_FAILED`. Add
  `--filesystem=/root/.ccr:ro --env=SSL_CERT_FILE=/root/.ccr/ca-bundle.crt`
  to `flatpak build`. With that, fetch → decode → reproject → colour
  takes 2.5 s in the sandbox (2026-10-24).
- **Map tiles**: GTK decodes the PNG tiles with glycin, which starts its
  loaders through `flatpak-spawn --sandbox`; under `flatpak build` in the
  container there is no Flatpak portal, so every tile fails with "Loader
  process exited early" and the map stays blank. Check tiles with the
  host run (`python3.12 -m cirro`) instead.

`--share=network` in the manifest is needed for radar data and map
tiles; no other permission beyond the toolkit defaults is used yet.
