"""The layer catalogue matches DWD's GeoServer (layer names recorded
from GetCapabilities on 2026-11-07)."""
from datetime import timedelta
from pathlib import Path

from cirro.layers import catalogue
from cirro.layers.timeaxis import parse_time, usable

NAMES = set((Path(__file__).parent / "data" / "wms" / "layer-names.txt")
            .read_text().split())


def test_ids_are_unique_and_groups_known():
    ids = [layer.id for layer in catalogue.LAYERS]
    assert len(ids) == len(set(ids))
    assert catalogue.RADAR not in ids
    assert {layer.group for layer in catalogue.LAYERS} <= set(catalogue.GROUPS)
    assert all(catalogue.in_group(group) for group in catalogue.GROUPS)


def test_every_wms_name_exists():
    for layer in catalogue.LAYERS:
        for i in range(max(1, len(layer.variants))):
            for name in layer.variant(i).wms:
                assert name in NAMES, f"{layer.id}[{i}]: {name}"


def test_roles_and_titles():
    for layer in catalogue.LAYERS:
        assert layer.role in (catalogue.BASE, catalogue.OVERLAY)
        assert layer.title and layer.title[0].isupper()
        assert 0 < layer.alpha <= 1


def test_variant_inherits_and_overrides():
    isobars = catalogue.get("isobars")
    assert isobars.variant(0).style == "icon-eu_reg00625_fd_sl_qff_isolines"
    assert isobars.variant(2).style == ""
    assert isobars.variant(2).wms == ("Icon_reg025_fd_sl_PMSL",)
    assert catalogue.get("pollen").variant(0).cql == "EC_II=1"
    # Out of range: the last one, not an error.
    assert catalogue.get("pollen").variant(99).label == "Ragweed"


def test_attributions():
    assert catalogue.BKG in catalogue.get("warnings").credits
    assert catalogue.EUMETSAT in catalogue.get("satellite").credits


def test_forecast_sums_skip_steps_without_data():
    run = "2026-11-07T06:00:00.000Z"
    start = parse_time(run)
    steps = [start + timedelta(hours=h) for h in range(0, 31, 3)]
    twelve = catalogue.get("precip-eu").variant(2)
    kept = usable(steps, run, twelve.lead, twelve.every)
    assert [(s - start).total_seconds() / 3600 for s in kept] == [12, 18, 24, 30]
    hourly = catalogue.get("precip-eu").variant(0)
    assert usable(steps, run, hourly.lead, hourly.every) == steps
    assert usable(steps, "", twelve.lead, twelve.every) == steps
