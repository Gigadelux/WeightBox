"""Phase 4 queries: a quick liveness and consistency read of the instance."""

from __future__ import annotations

VERSION = "SELECT version();"
DATABASE_SIZE_PRETTY = "SELECT pg_size_pretty(pg_database_size(current_database()));"
ACTIVE_CONNECTIONS = (
    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
)
VALIDATOR_ALL_PASS = (
    "SELECT count(*) = 0 FROM validator_fact_nulls WHERE status <> 'pass';"
)

# Relations to row-count in the health report.
ROW_COUNT_TARGETS: list[tuple[str, str]] = [
    ("ods", "ods_models"),
    ("ods", "ods_gpus"),
    ("ods", "reject_models"),
    ("ods", "reject_gpus"),
    ("public", "dim_model"),
    ("public", "dim_gpu"),
    ("public", "fact_gpu_model_compatibility"),
    ("public", "validator_fact_nulls"),
]

INDEX_TARGETS: list[str] = [
    "ix_fact_model_nk",
    "ix_fact_gpu_nk",
    "ix_fact_gpu_key",
    "ix_fact_model_key",
]
