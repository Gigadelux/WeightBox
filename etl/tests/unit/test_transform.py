from __future__ import annotations

import datetime as dt

import pytest

from src import transform

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "clock, bus, rate, expected",
    [
        (1750, 256, 8, 448.0),    # RTX 3070, GDDR6
        (1313, 384, 16, 1008.19),  # RTX 4090, GDDR6X
        (1215, 5120, 2, 1555.2),   # A100 40GB, HBM2e
    ],
)
def test_memory_bandwidth_matches_reference_cards(clock, bus, rate, expected):
    got = transform.memory_bandwidth_gbs(clock, bus, rate)
    assert got == pytest.approx(expected, rel=0.02)


def test_memory_bandwidth_missing_input_is_none():
    assert transform.memory_bandwidth_gbs(None, 256, 8) is None
    assert transform.memory_bandwidth_gbs(1750, None, 8) is None


def test_footprint_precision_scaling():
    fp16 = transform.model_footprint_gb(7e9, "fp16")
    int8 = transform.model_footprint_gb(7e9, "int8")
    int4 = transform.model_footprint_gb(7e9, "int4")
    assert fp16 == pytest.approx(7e9 * 2 * 1.20 / 1e9)
    assert int8 == pytest.approx(fp16 / 2)
    assert int4 == pytest.approx(fp16 / 4)
    assert transform.model_footprint_gb(None, "fp16") is None


def test_fits_and_headroom():
    fp16 = transform.model_footprint_gb(7e9, "fp16")  # 16.8 GB
    assert transform.fits_in_vram(fp16, 24) is True
    assert transform.fits_in_vram(fp16, 8) is False
    assert transform.vram_headroom_gb(fp16, 24) == pytest.approx(24 - fp16)
    assert transform.fits_in_vram(None, 24) is None
    assert transform.vram_headroom_gb(None, 24) is None


def test_quantization_ladder():
    assert transform.quantization_required(7e9, 24) == "none"      # 16.8 GB fp16
    assert transform.quantization_required(7e9, 12) == "8-bit"     # 8.4 GB int8
    assert transform.quantization_required(30e9, 24) == "4-bit"    # 18 GB int4
    assert transform.quantization_required(400e9, 24) == "does-not-fit"
    assert transform.quantization_required(None, 24) is None


def test_estimated_throughput_only_for_generative_with_params():
    fp16 = transform.model_footprint_gb(7e9, "fp16")
    assert transform.estimated_throughput(True, 7e9, 448.0, fp16) == pytest.approx(448.0 / fp16)
    assert transform.estimated_throughput(False, 7e9, 448.0, fp16) is None
    assert transform.estimated_throughput(True, None, 448.0, fp16) is None
    assert transform.estimated_throughput(True, 7e9, None, fp16) is None


def test_calendar_parts():
    assert transform.calendar_parts(dt.date(2024, 3, 14)) == (3, 1, 2024, 2020)
    assert transform.calendar_parts(dt.date(2019, 11, 2)) == (11, 4, 2019, 2010)


def test_parse_date_formats():
    assert transform.parse_date("2024-03-14") == dt.date(2024, 3, 14)
    assert transform.parse_date("2024") == dt.date(2024, 1, 1)
    assert transform.parse_date("garbage") is None


def test_parameter_bucket_edges():
    assert transform.parameter_bucket(None) == "unknown"
    assert transform.parameter_bucket(5e8) == "<1B"
    assert transform.parameter_bucket(7e9) == "7-13B"
    assert transform.parameter_bucket(2e11) == ">180B"


def test_vram_bucket_edges():
    assert transform.vram_bucket(4) == "<=4"
    assert transform.vram_bucket(8) == "6-8"
    assert transform.vram_bucket(24) == "24"
    assert transform.vram_bucket(80) == ">48"


def test_primary_domain_priority_and_fallback():
    assert transform.primary_domain("Multimodal,Language,Vision", None) == "Language"
    assert transform.primary_domain("Vision", None) == "Vision"
    assert transform.primary_domain(None, "speech recognition") == "Speech"
    assert transform.primary_domain(None, None) == "Other"


def test_plausible_parameter_count_bounds():
    assert transform.plausible_parameter_count("7000000000") == 7e9
    assert transform.plausible_parameter_count("16") is None
    assert transform.plausible_parameter_count("9e13") is None


def test_org_country_from_source_column_only():
    assert transform.org_country("United States of America") == "United States"
    assert transform.org_country("United States of America,France") == "United States"
    assert transform.org_country("China,China") == "China"
    assert transform.org_country("Korea (Republic of)") == "South Korea"
    assert transform.org_country("Germany") == "Germany"
    assert transform.org_country("") == "Unknown"
    assert transform.org_country(None) == "Unknown"
