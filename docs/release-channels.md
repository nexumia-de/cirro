---
type: Playbook
title: Release channels
description: Cirro (stable, from tags v<version>) and Cirro (Nightly) (de.nexumia.Cirro.Devel, from every push to main), how the nightly variant is built and how to release.
tags: [release, nightly, flatpak, ci, meson]
generated: { by: claude-code/2.1.310, at: 2026-10-25T16:00:00Z }
---

# Channels

| Channel | App | App id | Fed by |
|---|---|---|---|
| Stable | Cirro | `de.nexumia.Cirro` | tags `v0.2.0`, … |
| Nightly | Cirro (Nightly) | `de.nexumia.Cirro.Devel` | every push to `main` |

Both come from the shared repository `https://flatpak.nexumia.de/`, show
up as two apps in GNOME Software and install side by side with separate
settings and caches. Why main and tags, and not a label slot for pull
requests or a `nightly` branch: the toolkit's decision
[release channels from main and tags](../../phosh-toolkit/docs/decisions/release-channels.md).
The CI mechanics are in the toolkit's
[Flatpak workflow](../../phosh-toolkit/docs/flatpak-workflow.md#release-channels).

Pull requests are tested on the phone after merging, in the nightly
app. To try one before merging, install its CI artifact (see the
toolkit's Flatpak workflow, "Install on the phone"); that bundle has the
stable app id and replaces an installed stable Cirro.

# Nightly variant

The meson options in `meson_options.txt` select it:

- `-Dprofile=development`: app id `de.nexumia.Cirro.Devel` in
  `cirro/config.py` (generated from `cirro/config.py.in`), desktop file
  and metainfo, icon installed under that id. `build-aux/nightly.py`
  derives the desktop file and metainfo from the stable files in
  `data/` (name "Cirro (Nightly)", ids, no `<replaces>`), so `data/`
  stays the only source; meson's `validate-*` tests check the generated
  files. The window gets libadwaita's `devel` style class (striped
  header bar).
- `-Dbuild_label=<branch> · <commit>`: shown in the About dialog as
  "0.1.0 (main · 8534d2c)", so the phone always tells which commit is
  installed.

Run from the source tree, `cirro/config.py` does not exist and the app
is the stable one. Local nightly build:

```sh
meson setup _build -Dprofile=development -Dbuild_label="local"
meson test -C _build
```

CI passes both options by deriving a manifest from
`de.nexumia.Cirro.yml`; there is no second manifest to keep in sync.

# Release (stable)

1. Bump the version in `meson.build`, `cirro/__init__.py` and add a
   `<release version="…" date="…">` with a description at the top of
   `data/de.nexumia.Cirro.metainfo.xml` (`tests/test_metadata.py`
   checks that all three agree).
2. Merge that pull request.
3. Tag the merge commit and push the tag:

   ```sh
   git tag v0.2.0 && git push origin v0.2.0
   ```

CI fails the tag build if the tag does not match the newest metainfo
release, attaches the bundles to the GitHub Release `v0.2.0` and
notifies phosh-apps.

# Verified (2026-10-25, locally)

- `meson setup -Dprofile=development` installs
  `de.nexumia.Cirro.Devel.desktop`, `.metainfo.xml` and `.svg`;
  `desktop-file-validate` and `appstreamcli validate --no-net` pass on
  both profiles.
