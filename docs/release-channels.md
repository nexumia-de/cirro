---
type: Playbook
title: Release channels
description: Cirro (stable, from tags v<version>) and Cirro (Nightly) (de.nexumia.Cirro.Devel, from every push to main), how the nightly variant is built, how releases, release notes and screenshots are automated.
tags: [release, nightly, flatpak, ci, meson, changelog, screenshots]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:00:00Z }
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

Releases are automated with the toolkit's
[release workflow](../../phosh-toolkit/docs/releases.md); nobody edits
versions or `<release>` elements by hand.

1. Every pull request that users notice adds a fragment to
   `changelog.d/` (see its `README.md`); others get the label
   `no-changelog`. The required check `release / Changelog` enforces it.
2. Every Monday (or by hand: *Actions → Release → Run workflow*) the
   workflow opens the pull request "Release <version>": version bumped
   in `meson.build`, `cirro/__init__.py` and the metainfo
   (`tests/test_metadata.py` checks they agree), the fragments as the new
   `<release>`, the screenshot list pointing at the release's assets.
3. The owner checks the text and the `de.nexumia.Cirro-screenshots`
   artifact of its Flatpak run, and merges.
4. The merge tags `v<version>`; the tag build checks the tag against the
   metainfo, takes the screenshots, creates the GitHub Release with the
   metainfo text, bundles and screenshots, and notifies phosh-apps.

The workflow uses the secret `PUBLISH_TOKEN` as its `RELEASE_TOKEN`, so
it needs **Contents** and **Pull requests** read/write on this
repository (besides dispatching to phosh-apps). A tag can still be
pushed by hand (`git tag v0.2.0 && git push origin v0.2.0`) on a commit
whose newest metainfo release is `0.2.0`.

The release notes reach users in GNOME Software ("What's New"), in the
About dialog ("What's New", read from the installed metainfo by
`cirro/metainfo.py`) and on the GitHub Release. The nightly app gets a
development release `<next>~dev.<date>.<commit>` with the pending
fragments, so its About dialog shows what is new on `main`.

# Screenshots

`release.toml` lists the shots; CI takes each at 360×720 (scale 2) and
1000×700, light and dark, from the built Flatpak:

| Shot | State | Actions |
|---|---|---|
| `radar` | the current analysis ("Now") | – |
| `forecast` | +60 min | `app.step-time(12)` |

They use the recorded radar data in `tests/data/demo/`
(`CIRRO_DEMO_DATA`, see [radar architecture](radar-architecture.md)),
so they look the same in every run; only the OSM tiles come from the
network. To add a state, give it an `app.*` action (GTK does not export
`win.*` actions on D-Bus) that is a real feature, e.g. a keyboard
shortcut, and add a `[[screenshots.shot]]`. Taking them locally:
[dev environment](dev-environment.md).

# Verified (2026-10-25, locally)

- `meson setup -Dprofile=development` installs
  `de.nexumia.Cirro.Devel.desktop`, `.metainfo.xml` and `.svg`;
  `desktop-file-validate` and `appstreamcli validate --no-net` pass on
  both profiles.
