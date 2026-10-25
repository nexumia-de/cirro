---
type: Reference
title: Bundled dependencies
description: Every module the Flatpak bundles, with pinned version, licence, bundled sub-libraries and how updates are found.
tags: [dependencies, licensing, flatpak]
generated: { by: claude-code/2.1.310, at: 2026-10-25T22:00:00Z }
sources:
  - id: protobuf-c
    resource: https://github.com/protobuf-c/protobuf-c/releases/download/v1.5.2/protobuf-c-1.5.2.tar.gz
    title: protobuf-c 1.5.2 tarball (LICENSE)
  - id: libshumate
    resource: https://download.gnome.org/sources/libshumate/1.7/libshumate-1.7.0.tar.xz
    title: libshumate 1.7.0 tarball (COPYING, meson.build)
  - id: numpy
    resource: https://pypi.org/project/numpy/2.5.4/
    title: numpy 2.5.4 source archive (pyproject.toml license, LICENSE.txt and the vendored licences it lists)
  - id: h5py
    resource: https://pypi.org/project/h5py/3.16.0/
    title: h5py 3.16.0 source archive (LICENSE, licenses/)
  - id: hdf5
    resource: https://github.com/HDFGroup/hdf5/releases/tag/2.0.0
    title: HDF5 2.0.0 source archive (LICENSE)
  - id: build-tools
    resource: https://pypi.org/
    title: PyPI metadata of meson-python 0.22.1, pyproject-metadata 0.12.1, pkgconfig 1.6.0
---

# Rules

The shared rules are in
[../../phosh-toolkit/docs/licensing.md](../../phosh-toolkit/docs/licensing.md)
and
[../../phosh-toolkit/docs/dependency-updates.md](../../phosh-toolkit/docs/dependency-updates.md).
CI fails if a module of `de.nexumia.Cirro.yml` is missing here or
installs no licence files.

Cirro is `AGPL-3.0-or-later`. Every licence below allows redistribution
in a bundle with it. The GNOME runtime (GTK, libadwaita, libsoup,
json-glib, libportal, Python) is not bundled; Flathub distributes it under its own
terms.

# Modules

Checked against the pinned files on 2026-10-25 (checksums match the
manifest). Everything compiled is built from its source archive, as
Flathub requires for bundled dependencies (phosh-toolkit
[Flathub readiness](../../phosh-toolkit/docs/flathub.md)).

| Module | Version | Licence | Bundled inside | Update check |
|--------|---------|---------|----------------|--------------|
| `protobuf-c` | 1.5.2 | BSD-2-Clause[^protobuf-c] | – | GitHub releases (JSON checker) |
| `libshumate` | 1.7.0 | LGPL-2.1-or-later[^libshumate] | – | GNOME checker, stable only |
| `python3-build-tools` | meson-python 0.22.1, pyproject-metadata 0.12.1, pkgconfig 1.6.0 | MIT; MIT; MIT[^build-tools] | – (build only: pure-Python wheels, removed by `cleanup`, only the licence texts ship; Cython and packaging come from the GNOME SDK) | PyPI, one per wheel |
| `python3-numpy` | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0[^numpy] | – (built without BLAS/LAPACK) | PyPI sdist |
| `hdf5` | 2.0.0 | BSD-3-Clause[^hdf5] | – (zlib from the runtime; no szip) | GitHub releases (JSON checker) |
| `python3-h5py` | 3.16.0 | BSD-3-Clause[^h5py] | – (links the `hdf5` module) | PyPI sdist |

# Licence texts in the bundle

All under `/app/share/licenses/de.nexumia.Cirro/<module>/`:

- `protobuf-c/LICENSE`, `libshumate/COPYING`, `hdf5/LICENSE`: installed
  by `post-install`.
- `python3-numpy/`, `python3-h5py/`: the `dist-info/licenses/` trees pip
  writes from the source archives, including the vendored code's texts.
- `python3-build-tools/<package>/`: the licence files of the build tools.

# Source availability

libshumate is LGPL. CI publishes the source bundle
`de.nexumia.Cirro.Sources` next to every app bundle; it contains every
source archive the build used.

# Build time and the runtime's Python

numpy, HDF5 and h5py compile in the Flatpak build; CI caches the result
per manifest version, so only manifest changes pay for it. The source
archives do not depend on the runtime's Python version.

[^protobuf-c]: protobuf-c 1.5.2 tarball (LICENSE)
[^libshumate]: libshumate 1.7.0 tarball (COPYING, meson.build)
[^numpy]: numpy 2.5.4 source archive
[^h5py]: h5py 3.16.0 source archive
[^hdf5]: HDF5 2.0.0 source archive (LICENSE)
[^build-tools]: PyPI metadata of the build tools
