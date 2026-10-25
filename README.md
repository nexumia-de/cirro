# Cirro

Named after cirrus clouds (*cirro-* as in cirrostratus), the high
clouds that often announce rain a day ahead. Formerly *Wetterblick*.

Adaptive GTK4/libadwaita weather app for [Phosh](https://phosh.mobi/)
phones, modelled on the feature set of DWD's WarnWetter app. Focus: the
**rain radar with a 2-hour forecast** (DWD RADVOR nowcast) on a map,
animated from the past hour to +2 h.

Status: milestone M2, the animated radar from −60 min to +2 h with a
time bar and the own location; phone measurements and the first
release are still open. See [docs/roadmap.md](docs/roadmap.md).

Cirro is an independent project and not affiliated with the
Deutscher Wetterdienst (DWD). Weather data: DWD open data. Map data:
© OpenStreetMap contributors.

## Install

On the phone, open <https://flatpak.nexumia.de/> and tap
Cirro; GNOME Software installs it and keeps it updated. Cirro is
updated with every release (tag `v<version>`); *Cirro (Nightly)*, which
installs next to it, with every push to `main`. See
[docs/release-channels.md](docs/release-channels.md).

## Support

Cirro is free for everyone. If you want to support its development
and more free apps, you can do so on
[Liberapay](https://liberapay.com/suitably). What the money pays for
and which fees each platform takes:
[support](https://github.com/nexumia-de/phosh-toolkit/blob/main/docs/support.md).

## Development

This repository uses
[phosh-toolkit](https://github.com/nexumia-de/phosh-toolkit), checked out
next to it:

```
workspace/
  phosh-toolkit/
  cirro/
```

```sh
[ -d phosh-toolkit ] || git clone https://github.com/nexumia-de/phosh-toolkit.git
bash phosh-toolkit/setup.sh
```

Run from the source tree with `python3 -m cirro`, test with
`python3 -m pytest`. Details, including the Flatpak build:
[docs/dev-environment.md](docs/dev-environment.md).

Agent rules: [AGENTS.md](AGENTS.md). Knowledge bundle:
[docs/index.md](docs/index.md).

## License

GNU Affero General Public License v3.0 or later
(`AGPL-3.0-or-later`), see [LICENSE](LICENSE). Anyone who distributes
the app or a modified version, or offers it over a network, must
publish the complete source under the same license. Why:
[license decision](docs/decisions/license.md).

Contributions are accepted only under the terms in
[CONTRIBUTING.md](CONTRIBUTING.md).
