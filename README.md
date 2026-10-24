# Wetterblick

Adaptive GTK4/libadwaita weather app for [Phosh](https://phosh.mobi/)
phones, modelled on the feature set of DWD's WarnWetter app. Focus: the
**rain radar with a 2-hour forecast** (DWD RADVOR nowcast) on a map,
animated from the past hour to +2 h.

Status: planning. See [docs/roadmap.md](docs/roadmap.md).

Wetterblick is an independent project and not affiliated with the
Deutscher Wetterdienst (DWD). Weather data: DWD open data. Map data:
© OpenStreetMap contributors.

## Development

This repository uses
[phosh-toolkit](https://github.com/suitably/phosh-toolkit), checked out
next to it:

```
workspace/
  phosh-toolkit/
  wetterblick/
```

```sh
[ -d phosh-toolkit ] || git clone https://github.com/suitably/phosh-toolkit.git
bash phosh-toolkit/setup.sh
```

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
