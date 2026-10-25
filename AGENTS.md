@../phosh-toolkit/AGENTS.md

# Cirro

Weather app for Phosh, modelled on DWD's WarnWetter app. The rain radar
with its 2-hour forecast is the core feature; everything else is
secondary. The shared rules in ../phosh-toolkit/AGENTS.md apply as well.

- App id: `io.github.suitably.Cirro`.
- Plan and milestones: [docs/roadmap.md](docs/roadmap.md). Work on the
  current milestone first; do not start later milestones without asking.
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
