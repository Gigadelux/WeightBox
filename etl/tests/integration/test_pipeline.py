from __future__ import annotations

import pytest

from src.pipeline import Pipeline

pytestmark = pytest.mark.integration


def test_ods_holds_every_source_row(ran, db):
    assert db.row_count("ods", "ods_models") == 6
    assert db.row_count("ods", "ods_gpus") == 6
    assert db.fetch_scalar("SELECT count(*) FROM ods.load_audit") == 2
    assert db.row_count("public", "dim_gpu") == 3
    assert db.row_count("public", "dim_model") == 5


def test_dimensions_reflect_cleansing(ran, db):
    products = {r["product_name"] for r in db.fetch_all("SELECT product_name FROM dim_gpu")}
    assert "GeForce GTX 780" not in products  # pre-2016 dropped
    assert db.fetch_scalar(
        "SELECT count(*) FROM ods.reject_gpus WHERE rule = 'pre_2016'"
    ) >= 1
    assert db.fetch_scalar(
        "SELECT count(*) FROM ods.reject_gpus WHERE rule = 'unknown_memory_type'"
    ) >= 1
    models = {r["model_nk"] for r in db.fetch_all("SELECT model_nk FROM dim_model")}
    assert "Test-LLM-7B" in models  # duplicate collapsed to one
    assert db.fetch_scalar(
        "SELECT count(*) FROM ods.reject_models WHERE rule = 'duplicate_model'"
    ) >= 1


def test_fact_is_the_full_cross_product_with_names(ran, db):
    n_gpu = db.row_count("public", "dim_gpu")
    n_model = db.row_count("public", "dim_model")
    n_fact = db.row_count("public", "fact_gpu_model_compatibility")
    assert n_gpu > 0 and n_model > 0
    assert n_fact == n_gpu * n_model
    assert db.fetch_scalar(
        "SELECT count(*) FROM fact_gpu_model_compatibility "
        "WHERE model_nk IS NULL OR gpu_nk IS NULL"
    ) == 0


def test_null_measures_track_missing_parameters(ran, db):
    unknown = db.fetch_scalar(
        "SELECT count(*) FROM fact_gpu_model_compatibility f "
        "JOIN dim_model m ON m.model_key = f.model_key "
        "WHERE m.parameter_count IS NULL AND f.fits_in_vram IS NOT NULL"
    )
    assert unknown == 0


def test_materialized_views_are_populated(ran, db):
    for mv in (
        "mv_deployability_by_year_arch",
        "mv_gpu_generation_tradeoff",
        "mv_domain_accessibility",
    ):
        assert db.row_count("public", mv) > 0


def test_second_run_skips_ods_upload(ran, settings, db):
    pipe = Pipeline(settings)
    try:
        report = pipe.run()
    finally:
        pipe.close()
    assert report.ok
    assert db.fetch_scalar("SELECT count(*) FROM ods.load_audit") == 2
    init = next(p for p in report.phases if p.phase == "initialization")
    assert all(load["skipped"] for load in init.metrics["ods_loads"])
