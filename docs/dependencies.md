---
type: Reference
title: Bundled dependencies
description: Every module the Flatpak bundles, with pinned version, licence, bundled sub-libraries and how updates are found.
tags: [dependencies, licensing, flatpak]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
sources:
  - id: protobuf-c
    resource: https://github.com/protobuf-c/protobuf-c/releases/download/v1.5.2/protobuf-c-1.5.2.tar.gz
    title: protobuf-c 1.5.2 tarball (LICENSE)
  - id: libshumate
    resource: https://download.gnome.org/sources/libshumate/1.7/libshumate-1.7.0.tar.xz
    title: libshumate 1.7.0 tarball (COPYING, meson.build)
  - id: numpy
    resource: https://pypi.org/project/numpy/2.5.4/
    title: numpy 2.5.4 wheel (METADATA, dist-info/licenses/LICENSE.txt)
  - id: h5py
    resource: https://pypi.org/project/h5py/3.16.0/
    title: h5py 3.16.0 wheel (METADATA, dist-info/licenses, h5py.libs/)
  - id: libaec
    resource: https://github.com/MathisRosenhauer/libaec/blob/v1.1.4/LICENSE.txt
    title: libaec 1.1.4 LICENSE.txt and src/CMakeLists.txt
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
json-glib, Python) is not bundled; Flathub distributes it under its own
terms.

# Modules

Checked against the pinned files on 2026-10-25 (checksums match the
manifest).

| Module | Version | Licence | Bundled inside | Update check |
|--------|---------|---------|----------------|--------------|
| `protobuf-c` | 1.5.2 | BSD-2-Clause[^protobuf-c] | – | GitHub releases (JSON checker) |
| `libshumate` | 1.7.0 | LGPL-2.1-or-later[^libshumate] | – | GNOME checker, stable only |
| `python3-numpy` | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0[^numpy] | OpenBLAS (BSD-3-Clause), LAPACK (BSD-3-Clause-Open-MPI), libgfortran (GPL-3.0-or-later WITH GCC-exception-3.1), libquadmath (LGPL-2.1-or-later) | PyPI JSON, one query per arch |
| `python3-h5py` | 3.16.0 | BSD-3-Clause[^h5py] | HDF5 (BSD-3-Clause style), libaec 1.1.4 and libsz (BSD-2-Clause)[^libaec] | PyPI JSON, one query per arch |

# Licence texts in the bundle

All under `/app/share/licenses/de.nexumia.Cirro/<module>/`:

- `protobuf-c/LICENSE`, `libshumate/COPYING`: installed by `post-install`.
- `python3-numpy/`, `python3-h5py/`: the wheels' `dist-info/licenses/`
  trees, which include the texts of the libraries they bundle.
- `python3-h5py/libaec-LICENSE.txt`: the h5py wheels bundle libaec
  (`libaec.so.0.1.4`, `libsz.so.2.0.1`, which libaec 1.1.4 builds) but
  ship no licence text for it, so the manifest adds it from upstream.
  Update this file when h5py bundles another libaec version.

# Source availability

libshumate, libquadmath and libgfortran are (L)GPL. CI publishes the
source bundle `de.nexumia.Cirro.Sources` next to every app bundle; it
contains the libshumate tarball and the wheels as built. The wheels
contain the libquadmath and libgfortran binaries only: their source is
the GCC release the numpy wheel build used (see numpy's `LICENSE.txt`,
section "GCC runtime library"). Open point: link that exact GCC source
from this page once the numpy wheel build records its GCC version.

# Wheels and the runtime's Python

The wheel tags (`cp314`) follow the runtime's Python. The update checker
only finds `cp314` wheels; when a GNOME runtime update changes Python,
update the tags in the manifest's `url-query` together with
`runtime-version`.

[^protobuf-c]: protobuf-c 1.5.2 tarball (LICENSE)
[^libshumate]: libshumate 1.7.0 tarball (COPYING, meson.build)
[^numpy]: numpy 2.5.4 wheel (METADATA, dist-info/licenses/LICENSE.txt)
[^h5py]: h5py 3.16.0 wheel (METADATA, dist-info/licenses, h5py.libs/)
[^libaec]: libaec 1.1.4 LICENSE.txt and src/CMakeLists.txt
