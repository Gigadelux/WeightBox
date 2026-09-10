"""Index DDL, applied in Phase 3.

FACT_NAME_INDEXES are the two required by the brief: one on the fact's model
name, one on the fact's gpu name. The rest follow WEIGHTBOX_SPECS.md section 8.
"""

from __future__ import annotations

FACT_NAME_INDEXES: dict[str, str] = {
    "ix_fact_model_nk": "CREATE INDEX IF NOT EXISTS ix_fact_model_nk "
    "ON fact_gpu_model_compatibility (model_nk);",
    "ix_fact_gpu_nk": "CREATE INDEX IF NOT EXISTS ix_fact_gpu_nk "
    "ON fact_gpu_model_compatibility (gpu_nk);",
}

SUPPORTING_INDEXES: dict[str, str] = {
    "ix_fact_gpu_key": "CREATE INDEX IF NOT EXISTS ix_fact_gpu_key "
    "ON fact_gpu_model_compatibility (gpu_key);",
    "ix_fact_model_key": "CREATE INDEX IF NOT EXISTS ix_fact_model_key "
    "ON fact_gpu_model_compatibility (model_key);",
    "ix_fact_model_key_fits": "CREATE INDEX IF NOT EXISTS ix_fact_model_key_fits "
    "ON fact_gpu_model_compatibility (model_key) WHERE fits_in_vram;",
    "ix_dim_model_primary_domain": "CREATE INDEX IF NOT EXISTS ix_dim_model_primary_domain "
    "ON dim_model (primary_domain);",
    "ix_dim_model_release_year": "CREATE INDEX IF NOT EXISTS ix_dim_model_release_year "
    "ON dim_model (release_year);",
    "ix_dim_gpu_architecture": "CREATE INDEX IF NOT EXISTS ix_dim_gpu_architecture "
    "ON dim_gpu (gpu_architecture);",
    "ix_dim_gpu_vram_bucket": "CREATE INDEX IF NOT EXISTS ix_dim_gpu_vram_bucket "
    "ON dim_gpu (vram_bucket);",
}

ALL_INDEXES: dict[str, str] = {**FACT_NAME_INDEXES, **SUPPORTING_INDEXES}
