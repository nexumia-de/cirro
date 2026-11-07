"""Every DWD map layer Cirro offers (docs/map-layers.md).

A `Layer` is one row in the layer picker. A *base* layer fills the map
and owns the time bar (the radar is the built-in one); *overlays* are
drawn on top and follow the base layer's time. A layer can have
variants (the pollen type, the period of a precipitation total), each
a WMS layer name or a CQL filter. Adding a DWD layer is one entry here.
"""
from dataclasses import dataclass, field
from datetime import timedelta

RADAR = "radar"
BASE, OVERLAY = "base", "overlay"

# Picker order.
GROUPS = ("Precipitation", "Thunderstorms", "Warnings", "Wind", "Temperature",
          "Air Pressure", "Satellite", "Health", "Sea", "Stations", "Climate")

# Extra credits next to "Based on data from Deutscher Wetterdienst".
BKG = "Geometry © GeoBasis-DE / BKG"
EUMETSAT = "Satellite data © EUMETSAT"


@dataclass(frozen=True)
class Variant:
    label: str
    wms: tuple = ()        # WMS layer names; empty: the layer's own
    cql: str = ""          # CQL_FILTER
    style: str | None = None
    # Forecast sums exist only from `lead` after the model run and every
    # `every` (checked live, 2026-11-07); the time axis advertises more.
    lead: timedelta = timedelta(0)
    every: timedelta | None = None
    dims: tuple = ()       # other WMS dimensions: (name, value) pairs


@dataclass(frozen=True)
class Value:
    """How a tap on the map reads this layer (GetFeatureInfo)."""
    kind: str              # "number", "wind", "warning", "pollen", "health"
    unit: str = ""
    decimals: int = 0

    @property
    def fields(self):
        """Attributes to ask for. Vector layers otherwise send every
        polygon along: 2.4 MB for pollen instead of 1.4 KB (2026-11-07)."""
        return {"warning": ("EVENT", "SEVERITY"),
                "pollen": ("POLLENINT", "GEN"),
                "health": ("PARAMETER_VALUE", "GEN")}.get(self.kind, ())


@dataclass(frozen=True)
class Layer:
    id: str
    title: str
    group: str
    wms: tuple             # WMS layer names, drawn in one request
    role: str = BASE
    note: str = ""         # subtitle in the picker: source and area
    style: str | None = None
    past: timedelta = timedelta(0)    # how far back the time bar reaches
    variants: tuple = ()
    value: Value | None = None
    credits: tuple = ()
    legend: dict = field(default_factory=dict)   # German label → English
    unit: str = ""         # legend unit, instead of DWD's German one
    opacity: float | None = None   # default: 0.75 for base, 1 for overlays
    source: str = "wms"    # "wfs": station values drawn by Cirro
    field: str = ""        # WFS attribute with the value

    @property
    def alpha(self):
        if self.opacity is not None:
            return self.opacity
        return 0.75 if self.role == BASE else 1.0

    def variant(self, index):
        if not self.variants:
            return Variant("", self.wms, "", self.style)
        v = self.variants[min(max(index, 0), len(self.variants) - 1)]
        return Variant(v.label, v.wms or self.wms, v.cql,
                       v.style if v.style is not None else self.style,
                       v.lead, v.every, v.dims)


H = timedelta(hours=1)
D = timedelta(days=1)

# Translations of DWD's German legend and value labels.
POLLEN_LEVELS = ("none", "none to low", "low", "low to moderate",
                 "moderate", "moderate to high", "high")
POLLEN_LEGEND = {
    "keine Belastung": "None", "keine bis geringe Belastung": "None to low",
    "geringe Belastung": "Low", "geringe bis mittlere Belastung": "Low to moderate",
    "mittlere Belastung": "Moderate", "mittlere bis hohe Belastung": "Moderate to high",
    "hohe Belastung": "High"}
HEALTH_LEGEND = {
    "positiver Einfluss": "Positive effect", "kein Einfluss": "No effect",
    "geringe Gefährdung": "Low risk", "hohe Gefährdung": "High risk",
    "Hohe Gefährdung": "High risk"}
WARNING_LEGEND = {
    "UV-Warnungen": "UV", "Warnung vor Hitze": "Heat",
    "Warnung vor extremer Hitze": "Extreme heat",
    "Wetterwarnungen (Stufe 1)": "Level 1",
    "Warnungen vor markantem Wetter (Stufe 2)": "Level 2",
    "Unwetterwarnungen (Stufe 3)": "Level 3",
    "Warnungen vor extremem Unwetter (Stufe 4)": "Level 4",
    "Vorabinformation Unwetter": "Advance notice"}
LIGHTNING_LEGEND = {"Border": "Lightning area", "Forecast": "Forecast"}

_POLLEN = (("Hazel", 1), ("Alder", 2), ("Ash", 8), ("Birch", 3),
           ("Grasses", 4), ("Rye", 5), ("Mugwort", 6), ("Ragweed", 7))
_HEALTH = (("General well-being", 1), ("Asthma", 2),
           ("Low blood pressure", 3), ("High blood pressure", 4),
           ("Degenerative rheumatism", 5), ("Inflammatory rheumatism", 6))
_CWAM = (("Wave height", "SWH"), ("Wind-sea height", "SHWW"),
         ("Swell height", "SHTS"), ("Wind-sea period", "PPWW"),
         ("Swell period", "PPTS"), ("Wind-sea direction", "MDWW"),
         ("Swell direction", "MDTS"), ("Wind speed", "SP10M"),
         ("Wind direction", "DD10M"))
_CLIMATE = (("Mean temperature 1961–1990", "TAMM_17_1961_30"),
            ("Minimum temperature 1961–1990", "TADNMM_17_1961_30"),
            ("Maximum temperature 1961–1990", "TADXMM_17_1961_30"),
            ("Precipitation 1961–1990", "RSMS_17_1961_30"),
            ("Sunshine 1961–1990", "SDMS_17_1961_30"),
            ("Sunshine 1971–2000", "SDMS_17_1971_30"),
            ("Solar radiation 1981–2010", "SISMM_annual_map_normals_1981_30"),
            ("Frost days 1971–2000", "Frostdays_annual_map_normals_1971_30"),
            ("Summer days 1971–2000", "Summerdays_annual_map_normals_1971_30"),
            ("Snow days 1971–2000", "Snowdays_annual_map_normals_1971_30"),
            ("Mean wind 10 m 1981–2000", "BRD_1km_winddaten_10m"),
            ("Mean wind 80 m 1981–2000", "BRD_1km_winddaten_80m"))

TEMPERATURE = Value("number", "°C")
MM = Value("number", "mm", 1)

LAYERS = (
    # Precipitation
    Layer("precip-eu", "Precipitation Forecast", "Precipitation",
          ("Icon-eu_reg00625_fd_sl_TOTPREC01H",),
          note="ICON-EU model, Europe, ~7 km", value=MM,
          variants=(Variant("1 hour"),
                    Variant("3 hours", ("Icon-eu_reg00625_fd_sl_TOTPREC03H",)),
                    Variant("12 hours", ("Icon-eu_reg00625_fd_sl_TOTPREC12H",),
                            lead=12 * H, every=6 * H),
                    Variant("24 hours", ("Icon-eu_reg00625_fd_sl_TOTPREC24H",),
                            lead=24 * H),
                    Variant("Since model start", ("Icon-eu_reg00625_fd_sl_TOTPREC",)))),
    Layer("precip-global", "Precipitation Forecast, 7 Days", "Precipitation",
          ("Icon_reg025_fd_sl_TOTPREC06H",),
          note="ICON global model, ~28 km", value=MM,
          variants=(Variant("6 hours", lead=6 * H, every=6 * H),
                    Variant("12 hours", ("Icon_reg025_fd_sl_TOTPREC12H",),
                            lead=12 * H),
                    Variant("24 hours", ("Icon_reg025_fd_sl_TOTPREC24H",),
                            lead=24 * H),
                    Variant("Since model start", ("Icon_reg025_fd_sl_TOTPREC",)))),
    Layer("precip-chance", "Precipitation Probability", "Precipitation",
          ("Icon-eps_reg025_fd_sl_TOTPREC24H",),
          note="Chance in 24 h, ICON ensemble, 7 days",
          value=Value("number", "%"),
          variants=tuple(Variant(f"More than {mm} mm", lead=24 * H,
                                 dims=(("ENSEMBLE_PRODUCT", f"Probabilities:>{mm}mm"),))
                         for mm in (1, 5, 10, 20, 50))),
    Layer("precip-ai", "Precipitation Forecast, AI Model", "Precipitation",
          ("Aicon_reg025_fd_sl_TOTPREC06H",), note="AICON, ~28 km", value=MM,
          variants=(Variant("6 hours", lead=9 * H),
                    Variant("Since model start", ("Aicon_reg025_fd_sl_TOTPREC",)))),
    Layer("precip-measured", "Measured Precipitation", "Precipitation",
          ("RADOLAN-RW",), note="Radar calibrated with rain gauges, Germany",
          past=2 * D,
          variants=(Variant("1 hour"), Variant("6 hours", ("RADOLAN-SQ",)),
                    Variant("24 hours", ("SF-Produkt",)),
                    Variant("Daily", ("SF-Produkt_(0-24)",)),
                    Variant("72 hours", ("RADOLAN-D3",)),
                    Variant("7 days", ("RADOLAN-W1",)),
                    Variant("14 days", ("RADOLAN-W2",)),
                    Variant("21 days", ("RADOLAN-W3",)),
                    Variant("30 days", ("RADOLAN-W4",)),
                    Variant("Month to date", ("RADOLAN-SM",)),
                    Variant("Year to date", ("RADOLAN-SJ",)),
                    Variant("Hydrological year", ("RADOLAN-SY",)),
                    Variant("Season, % of normal", ("RADOLAN-prozZ",)),
                    Variant("Month, % of normal", ("RADOLAN-prozM",)),
                    Variant("Year, % of normal", ("RADOLAN-prozJ",)),
                    Variant("Hydrological year, % of normal", ("RADOLAN-prozY",)))),
    # Thunderstorms
    Layer("lightning", "Lightning Areas", "Thunderstorms", ("NCEW_EU",),
          role=OVERLAY, note="Detected and forecast lightning, to +3 h",
          past=3 * H, legend=LIGHTNING_LEGEND),
    Layer("lightning-density", "Lightning Density", "Thunderstorms",
          ("Blitzdichte",), role=OVERLAY, note="Strikes of the last 15 min",
          past=3 * H, opacity=0.85),
    Layer("storm-cells", "Thunderstorm Cells", "Thunderstorms",
          ("K3D_EVAL_current_cells", "K3D_EVAL_fcst_cone",
           "K3D_EVAL_fcst_track"),
          role=OVERLAY, note="Cell outlines and forecast path", past=3 * H),
    Layer("storm-clusters", "Thunderstorm Clusters", "Thunderstorms",
          ("Gewittercluster",), role=OVERLAY, note="Tracks of cell clusters",
          past=3 * H),
    Layer("flashes", "Lightning from Satellite", "Thunderstorms",
          ("Accumulated_Flash_Area",), role=OVERLAY,
          note="Meteosat Lightning Imager", past=H, credits=(EUMETSAT,),
          variants=(Variant("Flash area"),
                    Variant("Flash outlines", ("Accumulated_Flash_Geometry",)))),
    # Warnings
    Layer("warnings", "Weather Warnings", "Warnings",
          ("Warnungen_Gemeinden_vereinigt",), role=OVERLAY,
          note="Official DWD warnings", credits=(BKG,), opacity=0.7,
          value=Value("warning"), legend=WARNING_LEGEND,
          variants=(Variant("Municipalities"),
                    Variant("Municipalities, unmerged", ("Warnungen_Gemeinden",)),
                    Variant("Districts", ("Warnungen_Landkreise",)))),
    Layer("warnings-coast", "Coast and Lake Warnings", "Warnings",
          ("Warnungen_Kueste", "Warnungen_Binnenseen"), role=OVERLAY,
          credits=(BKG,), opacity=0.7, value=Value("warning"),
          legend=WARNING_LEGEND),
    Layer("autowarn", "Automatic Nowcast Warnings", "Warnings",
          ("Autowarn_Vorhersage",), role=OVERLAY,
          note="NowCastMIX, moved forward 60 min", past=3 * H,
          variants=(Variant("Forecast"),
                    Variant("Analysis", ("Autowarn_Analyse",)))),
    # Wind
    Layer("gusts", "Gust Probability", "Wind",
          ("Icon-eps_reg025_fd_sl_VMAX10M12H",),
          note="Chance in 12 h, ICON ensemble, 7 days",
          value=Value("number", "%"),
          variants=tuple(Variant(f"Gusts over {speed} m/s ({force} Bft)",
                                 dims=(("ENSEMBLE_PRODUCT", f"Probabilities:>{speed}m/s"),))
                         for speed, force in (("14", 7), ("18", 8), ("25", 10),
                                              ("29", 11), ("33", 12)))),
    Layer("gust-risk", "Storm Probability", "Wind",
          ("icon-d2-eps_ecwarn_reg002_fd_sl_pVMAX10MgtX",),
          note="Gusts > 29 m/s, ICON-D2 ensemble, Germany",
          value=Value("number", "%"),
          variants=(Variant("Germany, 2 days"),
                    Variant("Europe, 6 days",
                            ("icon-eu-eps_ecwarn_reg0125_fd_sl_pVMAX10MgtX",)))),
    Layer("wind-speed", "Wind Probability", "Wind",
          ("Icon-eps_reg025_fd_pl_SP10M",),
          note="Mean wind at 10 m, ICON ensemble, 7 days",
          value=Value("number", "%"),
          variants=tuple(Variant(f"Wind over {speed} m/s ({force} Bft)",
                                 dims=(("ENSEMBLE_PRODUCT", f"Probabilities:>{speed}m/s"),))
                         for speed, force in (("10", 5), ("14", 7), ("18", 8),
                                              ("25", 10)))),
    Layer("wind-barbs", "Wind Barbs", "Wind", ("Icon_reg025_fd_sl_UV10M",),
          role=OVERLAY, note="10 m, ICON global", value=Value("wind"),
          variants=(Variant("ICON global"),
                    Variant("AI model", ("Aicon_reg025_fd_sl_UV10M",)),
                    Variant("Sea", ("Ewam_reg005x010_fd_sl_UV10M",),
                            style="ewam_reg005x010_fd_sl_uv10m_windbarbs_epsg3857"))),
    Layer("icing", "Wet Snow and Freezing Rain", "Wind",
          ("icon-d2-eps_ecwarn_reg002_fd_sl_FP",),
          note="Probability of loads on power lines", value=Value("number", "%"),
          variants=(Variant("Germany, 2 days"),
                    Variant("Germany, windy", ("icon-d2-eps_ecwarn_reg002_fd_sl_FPW",)),
                    Variant("Europe, 6 days", ("icon-eu-eps_ecwarn_reg0125_fd_sl_FP",)),
                    Variant("Europe, windy", ("icon-eu-eps_ecwarn_reg0125_fd_sl_FPW",)))),
    # Temperature
    Layer("temperature", "Temperature", "Temperature",
          ("Icon-eu_reg00625_fd_gl_T",), note="2 m, ICON-EU, ~7 km",
          value=TEMPERATURE,
          variants=(Variant("Europe model"),
                    Variant("Global model, 7 days", ("Icon_reg025_fd_sl_T2M",)),
                    Variant("AI model", ("Aicon_reg025_fd_sl_T",)))),
    Layer("feels-like", "Feels-Like Temperature", "Temperature",
          ("GefuehlteTemp",), note="ICON-EU, 2 days", value=TEMPERATURE,
          variants=(Variant("Hourly"),
                    Variant("Daily maximum", ("GefuehlteTempMax",)),
                    Variant("Daily minimum", ("GefuehlteTempMin",)),
                    Variant("Time of maximum", ("GefuehlteTempMaxZeit",)),
                    Variant("Time of minimum", ("GefuehlteTempMinZeit",)))),
    # Air pressure
    Layer("isobars", "Isobars", "Air Pressure", ("Icon-eu_reg00625_fd_sl_QFF",),
          role=OVERLAY, note="Sea-level pressure, ICON-EU",
          style="icon-eu_reg00625_fd_sl_qff_isolines",
          value=Value("number", "hPa"),
          variants=(Variant("Europe model"),
                    Variant("Europe model, dense", style="icon-eu_reg00625_fd_sl_qff_isolines_dense"),
                    Variant("Global model", ("Icon_reg025_fd_sl_PMSL",), style=""),
                    Variant("AI model", ("Aicon_reg025_fd_sl_PMSL",), style=""),
                    Variant("Ensemble mean", ("Icon-eps_reg025_fd_sl_PMSL",), style="",
                            dims=(("ENSEMBLE_PRODUCT",
                                   "Products:Unweighted mean of all members"),)))),
    # Satellite
    Layer("satellite", "Satellite Image", "Satellite",
          ("Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h",),
          note="Meteosat, every 3 hours", past=2 * D, credits=(EUMETSAT,),
          variants=(Variant("Europe, colour"),
                    Variant("World, infrared",
                            ("Satellite_worldmosaic_3km_world_ir108_3h",)))),
    # Health
    Layer("pollen", "Pollen", "Health", ("Pollenflug",),
          note="DWD pollen index, Germany", value=Value("pollen"),
          credits=(BKG,), legend=POLLEN_LEGEND, opacity=0.7,
          variants=tuple(Variant(name, cql=f"EC_II={n}") for name, n in _POLLEN)),
    Layer("health", "Health Weather", "Health", ("Biowettervorhersage",),
          note="Weather effects on health, Germany", value=Value("health"),
          credits=(BKG,), legend=HEALTH_LEGEND, opacity=0.7,
          variants=tuple(Variant(name, cql=f"EC_II={n}") for name, n in _HEALTH)),
    Layer("uv", "UV Index", "Health", ("UVIndex",),
          note="Daily maximum, ICON-EU", value=Value("number", "", 1),
          variants=(Variant("Europe"), Variant("Europe, clear sky", ("UVI_CS",)),
                    Variant("World, cloudy", ("UVI_Global_CL",)),
                    Variant("World, clear sky", ("UVI_Global_CS",)),
                    Variant("Time of maximum", ("UVZeit",)),
                    Variant("Time of maximum, world", ("UVZeit_Global_CL",)))),
    Layer("uv-dose", "UV Dose", "Health", ("UV_Dosis_EU_CL",),
          note="Daily dose", value=Value("number", "", 2),
          variants=(Variant("Europe, cloudy"),
                    Variant("Europe, clear sky", ("UV_Dosis_EU_CS",)),
                    Variant("World, cloudy", ("UV_Dosis_Global_CL",)),
                    Variant("World, clear sky", ("UV_Dosis_Global_CS",)))),
    # Sea
    Layer("waves-coast", "Waves, German Coast", "Sea",
          ("Cwam_reg0013x0008_fd_sl_SWH",),
          note="German Bight and Baltic, ~900 m, 3 days",
          value=Value("number", "m", 1),
          variants=tuple(Variant(label, (f"Cwam_reg0013x0008_fd_sl_{code}",))
                         for label, code in _CWAM)),
    Layer("waves-europe", "Waves, Europe", "Sea",
          ("Ewam_reg005x010_fd_sl_SWH",), note="European seas, ~5 km, 5 days",
          value=Value("number", "m", 1),
          variants=tuple(Variant(label, (f"Ewam_reg005x010_fd_sl_{code}",))
                         for label, code in _CWAM)),
    # Stations: drawn by Cirro from WFS (cirro/layers/station_layer.py).
    Layer("stations-wind", "Measured Wind", "Stations", ("RBSN_FF",),
          role=OVERLAY, note="72 DWD stations, hourly; Beaufort force, arrow where it blows",
          past=2 * D, source="wfs", field="SPEED", value=Value("wind")),
    Layer("stations-temperature", "Measured Temperature", "Stations",
          ("RBSN_T2m",), role=OVERLAY, note="72 DWD stations, hourly",
          past=2 * D, source="wfs", field="TEMPERATURE", value=TEMPERATURE),
    Layer("stations-humidity", "Measured Humidity", "Stations", ("RBSN_RH",),
          role=OVERLAY, note="72 DWD stations, hourly", past=2 * D,
          source="wfs", field="REL_HUMIDITY", value=Value("number", "%")),
    Layer("stations-precip", "Measured Precipitation, Stations", "Stations",
          ("RBSN_RR",), role=OVERLAY, note="DWD stations, daily", past=7 * D,
          source="wfs", field="PRECIPITATION", value=MM),
    Layer("stations-evaporation", "Potential Evaporation", "Stations",
          ("RBSN_VPGB",), role=OVERLAY, note="DWD stations, daily", past=7 * D,
          source="wfs", field="EVAPOTRANSPIRATION", value=MM),
    # Climate
    Layer("climate", "Climate Maps", "Climate", (_CLIMATE[0][1],),
          note="Long-term means, Germany",
          variants=tuple(Variant(label, (name,)) for label, name in _CLIMATE)),
)

_BY_ID = {layer.id: layer for layer in LAYERS}


def get(layer_id):
    return _BY_ID.get(layer_id)


def in_group(group):
    return [layer for layer in LAYERS if layer.group == group]
