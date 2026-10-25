# Cirro

Named after cirrus clouds (*cirro-* as in cirrostratus), the high
clouds that often announce rain a day ahead. Formerly *Wetterblick*.

Adaptive GTK4/libadwaita weather app for [Phosh](https://phosh.mobi/)
phones, modelled on the feature set of DWD's WarnWetter app. Focus: the
**rain radar with a 2-hour forecast** (DWD RADVOR nowcast) on a map,
animated from the past hour to +2 h.

Status: milestone M1, a map with the current radar frame; animation
and forecast follow in M2. See
[docs/roadmap.md](docs/roadmap.md).

Cirro is an independent project and not affiliated with the
Deutscher Wetterdienst (DWD). Weather data: DWD open data. Map data:
© OpenStreetMap contributors.

## Install

On the phone, open <https://suitably.github.io/phosh-apps/> and tap
Cirro; GNOME Software installs it and keeps it updated. Every
push to `main` is published there.

## Development

This repository uses
[phosh-toolkit](https://github.com/suitably/phosh-toolkit), checked out
next to it:

```
workspace/
  phosh-toolkit/
  cirro/
```

```sh
[ -d phosh-toolkit ] || git clone https://github.com/suitably/phosh-toolkit.git
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
