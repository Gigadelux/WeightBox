from __future__ import annotations

import pandas as pd
import pytest

from src import cleansing
from SQL.tables.ods import ODS_GPUS_COLUMNS, ODS_MODELS_COLUMNS

pytestmark = pytest.mark.unit


def _gpu_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame([{c: r.get(c, "") for c in ODS_GPUS_COLUMNS} for r in rows])


def _model_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame([{c: r.get(c, "") for c in ODS_MODELS_COLUMNS} for r in rows])


def test_gpu_pre_2016_rows_are_rejected():
    df = _gpu_frame(
        [
            {"product_name": "RTX 3070", "release_year": "2020", "mem_size": "8",
             "mem_bus_width": "256", "mem_clock": "1750", "mem_type": "GDDR6"},
            {"product_name": "GTX 780", "release_year": "2013", "mem_size": "3",
             "mem_bus_width": "384", "mem_clock": "1502", "mem_type": "GDDR5"},
        ]
    )
    result = cleansing.cleanse_gpus(df)
    assert "GTX 780" not in set(result.frame["product_name"])
    assert any(r["rule"] == "pre_2016" for r in result.rejects)


def test_gpu_junk_memtype_rejected_and_dirty_variant_accepted():
    df = _gpu_frame(
        [
            {"product_name": "RTX 4090", "release_year": "2022", "mem_size": "24",
             "mem_bus_width": "", "mem_clock": "1313", "mem_type": " GDDR6X",
             "gpu_chip": "AD102"},
            {"product_name": "Junk Card", "release_year": "2021", "mem_size": "8",
             "mem_bus_width": "128", "mem_clock": "1500", "mem_type": "VRAM"},
        ]
    )
    result = cleansing.cleanse_gpus(df)
    names = set(result.frame["product_name"])
    assert "RTX 4090" in names
    assert "Junk Card" not in names
    assert any(r["rule"] == "unknown_memory_type" for r in result.rejects)
    row = result.frame.loc[result.frame["product_name"] == "RTX 4090"].iloc[0]
    assert row["mem_type"] == "GDDR6X"
    assert row["mem_bus_width_bit"] == 384  # imputed from the curated map
    assert bool(row["bandwidth_is_estimated"]) is True


def test_gpu_duplicate_product_name_collapses_to_most_complete():
    df = _gpu_frame(
        [
            {"product_name": "RTX 3070", "release_year": "2020", "mem_size": "8",
             "mem_bus_width": "", "mem_clock": "", "mem_type": "GDDR6"},
            {"product_name": "RTX 3070", "release_year": "2020", "mem_size": "8",
             "mem_bus_width": "256", "mem_clock": "1750", "mem_type": "GDDR6",
             "gpu_chip": "GA104", "gpu_clock": "1500"},
        ]
    )
    result = cleansing.cleanse_gpus(df)
    assert list(result.frame["product_name"]).count("RTX 3070") == 1
    assert any(r["rule"] == "duplicate_product_name" for r in result.rejects)
    row = result.frame.iloc[0]
    assert row["mem_clock_mhz"] == 1750


def test_model_domain_priority_and_org_alias():
    df = _model_frame(
        [
            {"model": "M1", "organization": "Google", "publication_date": "2024-03-14",
             "domain": "Multimodal,Language,Vision", "parameters": "7000000000",
             "country_of_organization": "United States of America,France"},
        ]
    )
    result = cleansing.cleanse_models(df)
    row = result.frame.iloc[0]
    assert row["primary_domain"] == "Language"
    assert bool(row["is_generative"]) is True
    assert row["organization"] == "Google DeepMind"
    # first comma-segment, verbose UN name shortened; org name is not consulted
    assert row["organization_country"] == "United States"
    assert row["release_quarter"] == 1


def test_model_country_falls_back_to_unknown_when_source_blank():
    df = _model_frame(
        [{"model": "M9", "organization": "OpenAI", "publication_date": "2024-01-01",
          "domain": "Language", "country_of_organization": ""}]
    )
    row = cleansing.cleanse_models(df).frame.iloc[0]
    assert row["organization_country"] == "Unknown"


def test_model_missing_parameters_kept_with_unknown_bucket():
    df = _model_frame(
        [
            {"model": "M2", "organization": "Anthropic", "publication_date": "2025-01-09",
             "domain": "Language", "parameters": ""},
        ]
    )
    result = cleansing.cleanse_models(df)
    row = result.frame.iloc[0]
    assert pd.isna(row["parameter_count"]) or row["parameter_count"] is None
    assert row["parameter_bucket"] == "unknown"
    assert "parameter_missing" in result.rule_counts


def test_model_bad_date_rejected():
    df = _model_frame(
        [{"model": "M3", "publication_date": "not-a-date", "domain": "Language"}]
    )
    result = cleansing.cleanse_models(df)
    assert result.frame.empty
    assert any(r["rule"] == "bad_publication_date" for r in result.rejects)
