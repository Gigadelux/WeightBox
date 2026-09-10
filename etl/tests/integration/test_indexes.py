from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

_REQUIRED = ["ix_fact_model_nk", "ix_fact_gpu_nk"]
_SUPPORTING = [
    "ix_fact_gpu_key",
    "ix_fact_model_key",
    "ix_fact_model_key_fits",
    "ix_dim_model_primary_domain",
    "ix_dim_gpu_architecture",
]


def test_required_fact_name_indexes_exist(ran, db):
    for name in _REQUIRED:
        assert db.index_exists(name), name
    rows = db.fetch_all(
        "SELECT indexname, indexdef FROM pg_indexes "
        "WHERE tablename = 'fact_gpu_model_compatibility'"
    )
    defs = {r["indexname"]: r["indexdef"] for r in rows}
    assert "model_nk" in defs["ix_fact_model_nk"]
    assert "gpu_nk" in defs["ix_fact_gpu_nk"]


def test_supporting_indexes_exist(ran, db):
    for name in _SUPPORTING:
        assert db.index_exists(name), name
