from __future__ import annotations

import pytest

from src import lookups, transform

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw, mem_type, family",
    [
        ("GDDR6", "GDDR6", "GDDR"),
        (" GDDR6 ", "GDDR6", "GDDR"),
        ("gddr6x", "GDDR6X", "GDDR"),
        ("HBM2e", "HBM2e", "HBM"),
        (" HBM3 ", "HBM3", "HBM"),
        ("GDDR7", "GDDR7", "GDDR"),
        ("LPDDR5", "LPDDR5", "LPDDR"),
    ],
)
def test_mem_type_table_covers_dirty_variants(raw, mem_type, family):
    got = transform.canonical_mem_type(raw)
    assert got is not None
    assert got[0] == mem_type
    assert got[1] == family


@pytest.mark.parametrize("junk", ["VRAM", "DRAM", "SGR", "CDRAM", "", "unknown"])
def test_junk_mem_tokens_reject(junk):
    assert transform.canonical_mem_type(junk) is None


def test_data_rate_is_not_a_function_of_family():
    """GDDR spans several data rates, so mem_family cannot determine it."""
    gddr_rates = {
        v[2] for k, v in lookups.MEM_TYPE_TABLE.items() if v[1] == "GDDR"
    }
    assert len(gddr_rates) >= 3
    assert lookups.MEM_TYPE_TABLE["GDDR5"][2] < lookups.MEM_TYPE_TABLE["GDDR6X"][2]


def test_domain_maps_agree():
    assert set(lookups.DOMAIN_GENERATIVE) == set(lookups.DOMAIN_PRIORITY)
    for domain, (is_gen, unit) in lookups.DOMAIN_GENERATIVE.items():
        assert (unit is None) == (not is_gen), domain


@pytest.mark.parametrize(
    "chip, product, arch",
    [
        ("AD102", "GeForce RTX 4090", "Ada Lovelace"),
        ("GA104", "GeForce RTX 3070", "Ampere"),
        ("Navi 21", "Radeon RX 6800", "RDNA 2"),
        ("", "Arc A770", "Arc Alchemist"),
        ("Mystery", "Unknown Card", "Unknown"),
    ],
)
def test_architecture_resolution(chip, product, arch):
    assert transform.gpu_architecture(chip, product) == arch
