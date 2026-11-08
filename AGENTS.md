@../phosh-toolkit/agents/core.md
@../phosh-toolkit/agents/gtk-app.md

# Cirro

Weather app for Phosh, modelled on DWD's WarnWetter app. The rain radar
with its 2-hour forecast is the core feature; everything else is
secondary.

- App id: `de.nexumia.Cirro`. Visible name: **Weather Radar** (chosen by
  the owner on 2026-11-06, [decision](docs/decisions/app-name.md)); the
  code name Cirro stays for the repository, app id, package, docs and
  `User-Agent`.
- Plan: [milestones](https://github.com/nexumia-de/cirro/milestones); goals in [docs/roadmap.md](docs/roadmap.md).
- Data sources and their open questions:
  [docs/data-sources.md](docs/data-sources.md). Verify every unverified
  fact there against the live service before building on it, and record
  the result in that file.
- Only use open data that may be redistributed (DWD open data, OSM).
  Never scrape the WarnWetter app's private backend and never use DWD
  branding, logos or the name "WarnWetter" in the UI or metadata.
- The app talks to public services directly; there is no own backend.
- Send a descriptive `User-Agent` (`Cirro/<version> (+repo URL)`)
  with every HTTP request and cache responses; OSM tile usage policy
  requires both.
- The cloud dev environment needs these hosts allowed:
  [docs/dev-environment.md](docs/dev-environment.md).
