from __future__ import annotations

import pytest

from services.schema_validator import SchemaValidator

pytestmark = pytest.mark.integration

_NULLABLE = {
    "model_vram_footprint_gb",
    "fits_in_vram",
    "vram_headroom_gb",
    "quantization_required",
    "estimated_throughput",
    "throughput_unit",
}


def test_validator_table_initialised_and_all_pass(ran, db):
    rows = db.fetch_all("SELECT attribute, status, null_count, checked_at FROM validator_fact_nulls")
    assert {r["attribute"] for r in rows} == _NULLABLE
    assert all(r["status"] == "pass" for r in rows)
    assert all(r["checked_at"] is not None for r in rows)


def test_validator_detects_a_broken_null_rule(ran, db):
    # Break the throughput_unit rule: set a unit where throughput is NULL.
    db.execute(
        "UPDATE fact_gpu_model_compatibility SET throughput_unit = 'tokens/sec' "
        "WHERE (gpu_key, model_key) IN ("
        "  SELECT gpu_key, model_key FROM fact_gpu_model_compatibility "
        "  WHERE estimated_throughput IS NULL LIMIT 1)"
    )
    results = SchemaValidator(db).check_fact_null_validator()
    by_attr = {r.attribute: r for r in results}
    assert by_attr["throughput_unit"].status == "fail"
    assert by_attr["fits_in_vram"].status == "pass"
