---
type: Plan
title: Map layers
description: Every DWD GeoServer layer, sorted into what Cirro shows, what it may show later and what it leaves out; the foundation all layers share and the issue for each group.
tags: [map, layers, wms, wfs, dwd, plan]
generated: { by: claude-code/2.1.310, at: 2026-11-07T11:45:00Z }
---

# Goal

The owner wants every useful DWD map layer in Cirro (2026-11-07). The
radar stays the default and keeps its own fast path
([radar architecture](radar-architecture.md)); every other layer comes
from DWD's GeoServer `https://maps.dwd.de/geoserver/dwd/`. Facts about
the service are in [data sources](data-sources.md), section 11.

# Foundation (M4)

All layers need the same four parts. The warning overlay #22 (M4) is
the first user, so they come with M4:

| Part | Issue |
|---|---|
| Layer catalogue and WMS image source: one `GetMap` image for the visible area, exact `TIME` steps from `GetCapabilities`, disk cache | [#24](https://github.com/nexumia-de/cirro/issues/24) |
| Layer picker: one base layer plus overlays, grouped, remembered | [#60](https://github.com/nexumia-de/cirro/issues/60) |
| Time bar for each layer's time steps (5 min … 1 day, up to +7.5 days) | [#61](https://github.com/nexumia-de/cirro/issues/61) |
| Own English legends in theme colours; the value at a tapped point (`GetFeatureInfo`) | [#62](https://github.com/nexumia-de/cirro/issues/62) |

With these in place, adding any DWD layer is one catalogue entry; the
issues below decide which ones and how they are presented.

# Layers Cirro shows

| Group | Layers (WMS names, shortened) | Issue | Milestone |
|---|---|---|---|
| Precipitation radar | own RV decoder (default base layer) | – | done |
| Warnings | `Warnungen_Gemeinden_vereinigt`, `Warnungen_Gemeinden`, `_Kueste`, `_Binnenseen`, `_Landkreise`; `Autowarn_Analyse`, `_Vorhersage` | [#22](https://github.com/nexumia-de/cirro/issues/22) | M4 |
| Lightning, thunderstorms | `Blitzdichte`, `NCEW_EU`, `Gewittercluster`, `K3D_EVAL_*`, `Accumulated_Flash_Area`, `Accumulated_Flash_Geometry` | [#63](https://github.com/nexumia-de/cirro/issues/63) | M6 |
| Satellite | `Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h`, `Satellite_worldmosaic_3km_world_ir108_3h` | [#64](https://github.com/nexumia-de/cirro/issues/64) | M6 |
| Temperature | `Icon_reg025_fd_sl_T2M`, `Aicon_reg025_fd_sl_T`, `Icon-eu_reg00625_fd_gl_T`, `GefuehlteTemp*`, `RBSN_T2m` | [#65](https://github.com/nexumia-de/cirro/issues/65) | M6 |
| Precipitation forecast and totals | `Icon-eu_…_TOTPREC01H/03H/12H/24H`, `Icon_…_TOTPREC06H/12H/24H`, `Icon-eps_…_TOTPREC24H`, the accumulated `…_TOTPREC` of ICON, ICON-EU and AICON (`Aicon_…_TOTPREC`, `…06H`); `RADOLAN-RW/SQ/D3/W1–W4/SM/SJ/SY`, `RADOLAN-prozJ/M/Y/Z`, `SF-Produkt`, `SF-Produkt_(0-24)`, `RBSN_RR` | [#66](https://github.com/nexumia-de/cirro/issues/66) | M6 |
| Wind arrows, wind at a place | WFS `RBSN_FF` | [#58](https://github.com/nexumia-de/cirro/issues/58), [#59](https://github.com/nexumia-de/cirro/issues/59) | M6 |
| Gusts, severe weather probabilities | `Icon-eps_…_VMAX10M12H`, `icon-d2-eps_ecwarn_…_pVMAX10MgtX`, `icon-eu-eps_ecwarn_…`, `…_FP`, `…_FPW`, `Icon_…_UV10M`, `Aicon_…_UV10M` | [#67](https://github.com/nexumia-de/cirro/issues/67) | M6 |
| Air pressure | `Icon-eu_…_QFF` (isobars), `Icon_…_PMSL`, `Aicon_…_PMSL`, `Icon-eps_…_PMSL` | [#68](https://github.com/nexumia-de/cirro/issues/68) | M6 |
| Pollen, UV, health weather | `Pollenflug`, `Biowettervorhersage`, `UVIndex`, `UVZeit`, `UVZeit_Global_CL`, `UVI_*`, `UV_Dosis_*` | [#69](https://github.com/nexumia-de/cirro/issues/69) | M6 |
| Sea state | `Cwam_…_*`, `Ewam_…_*` (wave height, period, direction) | [#70](https://github.com/nexumia-de/cirro/issues/70) | M6 |
| Station measurements | `RBSN_T2m`, `RBSN_RH`, `RBSN_RR`, `RBSN_VPGB` (WFS) | [#71](https://github.com/nexumia-de/cirro/issues/71) | M6 |
| Climate maps (30-year means) | `TAMM/TADNMM/TADXMM_…`, `RSMS_…`, `SDMS_…`, `SISMM_…`, `*days_annual_map_normals_*`, `BRD_1km_winddaten_*` | [#72](https://github.com/nexumia-de/cirro/issues/72) | backlog |

# Left out, and why

The remaining layers are not weather for the public, duplicate a layer
above, or are base maps Cirro already has from OSM. A catalogue entry
can still add any of them later.

- **Duplicates of the radar**: `Niederschlagsradar` (alias of RV),
  `Radar_rv_product_1x1km_ger`, `Radar_wn-analysis_1x1km_ger`,
  `Radar_wn-product_1x1km_ger` (reflectivity), `RADOLAN-RY`. Cirro decodes RV itself.
- **Upper air, for experts**: `Icon_reg025_fd_pl_*` and
  `Icon-eps_reg025_fd_pl_*` (geopotential, temperature, humidity, wind
  and vertical motion on pressure levels), `Hoehe_icon`.
- **Network monitoring**: `CLIMAT_*`, `INPUT_FORMAT_*`,
  `MONTH_YEAR_GROUP`, `PERCENTAGE_CLIMAT_REGION`,
  `PERFORMANCE_INDICATOR*`, `EUCOS_*`, `Ceilometer`, `E-PROFILE`,
  `Trajectories`, `Polarstern` (2019–2020 expedition),
  `ICON-EPS_meteograms`, `EEVIEW_*`, `Prob_sunny_days`, `Uv_Stationen`.
- **Special simulations**: `ORKA-DE_*` (cold-air flow simulations
  for planning), `K3D_EVAL_available_timestamps`.
- **Base maps and boundaries**: `Natural_Earth_Map`, `bluemarble`,
  `GRAY_HR_SR_OB_DR`, `Laender`, `VG250_Gemeinden`,
  `KV_VG250_BUNDESLAENDER_2020`, `BRD_Orte`, `Gewaesser`,
  `Gewaessernetz_Deutschland_fein`, `Einzugsgebiete_DE`,
  `Lat_Lon_Gitternetz`, `ne_10m_graticules`, `WMO_REGIONS`,
  `Icon-eu_Modelarea`, `dominant_landuse`, `depth_to_rock`,
  `euro24_poi`, and the warning *areas* `Warngebiete_*`,
  `Pollenfluggebiete` and `Biowettergebiete` (the layers above already
  draw them filled).

# Design rules for every layer

- English titles and legends of Cirro's own; DWD's legend images are
  German, black on white and have no dark mode.
- Colour is never the only carrier: legend labels, and the tap value
  in words ([design](../../phosh-toolkit/docs/design.md)).
- "Source: Deutscher Wetterdienst" stays visible next to the map for
  every DWD layer. Layers with geometry from others carry that note
  too: the warning areas say "Copyright GeoBasis-DE / BKG 2019 (Daten
  modifiziert)" in their abstract (`Warngebiete_*`, `VG250_Gemeinden`),
  so the warning layers drawn on them get the BKG note as well (as in
  the [warning decision](decisions/warning-product.md)). Satellite
  images (EUMETSAT) get their attribution checked before release.
- Bandwidth: one image per view and time step (2–130 KB at 230×300 px
  on 2026-11-07), cached on disk; measure on the phone with the first
  layers.
