"""Will it start raining at one point soon? The 2-hour RV series at the
point from one `GetFeatureInfo` of DWD's radar WMS (≈ 5 KB) instead of
the 2–12 MB tar the map needs (docs/data-sources.md, section 2). No GTK."""
import json
from datetime import datetime, timedelta

from cirro.layers import wms
from cirro.layers.timeaxis import format_time
from cirro.nowcast import RAIN

LAYER = "Radar_rv_product_1x1km_ger"
# Notify when rain starts within this time.
LEAD = timedelta(minutes=30)
FORECAST = timedelta(minutes=120)


def series_url(latitude, longitude, analysis_time, reference_time):
    url = wms.feature_info_url([LAYER], latitude, longitude,
                               reference_time=reference_time)
    end = analysis_time + FORECAST
    return f"{url}&time={format_time(analysis_time)}/{format_time(end)}"


def parse_series(body):
    """GetFeatureInfo JSON → [(valid time, mm/h)], in time order. The
    WMS value is mm per 5 min like the RV file; negative means dry."""
    series = []
    for feature in json.loads(body).get("features", []):
        properties = feature.get("properties", {})
        value = properties.get("RV_ANALYSIS")
        when = properties.get("TIME")
        if value is None or not when:
            continue
        time_ = datetime.fromisoformat(when.replace("Z", "+00:00"))
        series.append((time_, max(0.0, float(value)) * 12))
    return sorted(series)


def fetch_series(latitude, longitude):
    caps = wms.fetch_capabilities(LAYER)
    analysis_time = caps.axis.last - FORECAST
    body, kind = wms.get(series_url(latitude, longitude, analysis_time,
                                    caps.reference_time))
    return parse_series(body)


def starts_in(series, now):
    """Minutes until rain starts within LEAD, or None: None too when it
    rains already (no notification for rain the user sees)."""
    past = [rate for time_, rate in series if time_ <= now]
    if past and past[-1] >= RAIN:
        return None
    for time_, rate in series:
        if now < time_ <= now + LEAD and rate >= RAIN:
            return max(0, round((time_ - now).total_seconds() / 60))
    return None
