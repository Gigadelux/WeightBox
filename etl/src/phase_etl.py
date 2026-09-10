"""Phase 2: ODS to star schema (Refresh).

Reads only the ODS tables, cleanses, transforms, truncates and reloads the two
dimensions, seeds and builds the fact, checks the validator table and the
post-load invariants, and refreshes the materialized views. Cleansing and
validator results are logged, not written to a file.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from data.models import PhaseReport
from services.config import Settings
from services.postgres import PostgresConnector
from services.schema_validator import SchemaValidator
from src import cleansing
from src.cleansing import CleanResult
from src.lookups import OVERHEAD_FACTOR
from SQL.queries import fact_build, refresh
from SQL.tables.star import DIM_GPU, DIM_MODEL

log = logging.getLogger("weightbox.etl.phase2")

_REJECT_INSERT = (
    "INSERT INTO ods.{table} (natural_key, rule, detail) VALUES (%s, %s, %s)"
)


def run(db: PostgresConnector, settings: Settings) -> PhaseReport:
    started = datetime.now(timezone.utc)
    errors: list[str] = []
    metrics: dict[str, object] = {}
    validator = SchemaValidator(db)

    ods_models = db.read_df("SELECT * FROM ods.ods_models")
    ods_gpus = db.read_df("SELECT * FROM ods.ods_gpus")
    metrics["ods_rows"] = {"models": len(ods_models), "gpus": len(ods_gpus)}

    model_clean = cleansing.cleanse_models(ods_models)
    gpu_clean = cleansing.cleanse_gpus(ods_gpus)
    _persist_rejects(db, "reject_models", model_clean)
    _persist_rejects(db, "reject_gpus", gpu_clean)
    metrics["rule_counts"] = {"models": model_clean.rule_counts, "gpus": gpu_clean.rule_counts}
    metrics["dim_rows"] = {"models": len(model_clean.frame), "gpus": len(gpu_clean.frame)}

    if model_clean.frame.empty or gpu_clean.frame.empty:
        raise RuntimeError("cleansing produced an empty dimension frame")

    db.execute(fact_build.TRUNCATE_STAR)
    db.copy_df(gpu_clean.frame, schema="public", table="dim_gpu",
               columns=DIM_GPU.insertable_columns())
    db.copy_df(model_clean.frame, schema="public", table="dim_model",
               columns=DIM_MODEL.insertable_columns())

    validator.initialize_fact_null_validator()
    db.execute(fact_build.INSERT_FACT, {"overhead": OVERHEAD_FACTOR})

    _assert_post_load(db, metrics)

    validator_rows = validator.check_fact_null_validator()
    failed = [r for r in validator_rows if r.status != "pass"]
    metrics["validator"] = {
        "rows": [r.model_dump(mode="json") for r in validator_rows],
        "failed": len(failed),
    }
    if failed and settings.etl_fail_fast:
        raise RuntimeError(
            "validator_fact_nulls failures: "
            + ", ".join(f"{r.attribute} ({r.detail})" for r in failed)
        )

    for stmt in refresh.refresh_statements():
        db.execute(stmt)
    db.execute(refresh.ANALYZE)

    _log_quality_summary(db, model_clean, gpu_clean, metrics)

    finished = datetime.now(timezone.utc)
    return PhaseReport(
        phase="etl",
        ok=not errors and not failed,
        started_at=started,
        finished_at=finished,
        metrics=metrics,
        errors=errors,
    )


def _persist_rejects(db: PostgresConnector, table: str, result: CleanResult) -> None:
    if not result.rejects:
        return
    rows = [(r["natural_key"], r["rule"], r.get("detail")) for r in result.rejects]
    with db.transaction() as conn, conn.cursor() as cur:
        cur.executemany(_REJECT_INSERT.format(table=table), rows)


def _assert_post_load(db: PostgresConnector, metrics: dict[str, object]) -> None:
    fact_rows = int(db.fetch_scalar(fact_build.COUNT_FACT) or 0)
    expected = int(db.fetch_scalar(fact_build.COUNT_EXPECTED) or 0)
    metrics["fact_rows"] = fact_rows
    metrics["fact_expected"] = expected
    checks = {
        "row_count": fact_rows == expected,
        "no_orphan_fks": int(db.fetch_scalar(fact_build.ORPHAN_FKS) or 0) == 0,
        "does_not_fit_consistent": int(db.fetch_scalar(fact_build.DOES_NOT_FIT_CONSISTENCY) or 0) == 0,
        "nk_populated": int(db.fetch_scalar(fact_build.NK_POPULATED) or 0) == 0,
    }
    metrics["post_load_checks"] = checks
    broken = [name for name, ok in checks.items() if not ok]
    if broken:
        raise RuntimeError(f"post-load assertions failed: {', '.join(broken)}")


def _log_quality_summary(
    db: PostgresConnector,
    model_clean: CleanResult,
    gpu_clean: CleanResult,
    metrics: dict[str, object],
) -> None:
    reject_models = db.row_count("ods", "reject_models")
    reject_gpus = db.row_count("ods", "reject_gpus")
    validator = metrics.get("validator", {})

    log.info("data quality summary")
    log.info(
        "  rows  models: ods=%s dim=%s reject=%s",
        metrics["ods_rows"]["models"], metrics["dim_rows"]["models"], reject_models,
    )
    log.info(
        "  rows  gpus:   ods=%s dim=%s reject=%s",
        metrics["ods_rows"]["gpus"], metrics["dim_rows"]["gpus"], reject_gpus,
    )
    log.info(
        "  rows  fact:   %s (expected %s)",
        metrics.get("fact_rows"), metrics.get("fact_expected"),
    )
    for rule, n in sorted(model_clean.rule_counts.items()):
        log.info("  model rule  %-28s %s", rule, n)
    for rule, n in sorted(gpu_clean.rule_counts.items()):
        log.info("  gpu rule    %-28s %s", rule, n)
    log.info("  validator failed: %s", validator.get("failed", "n/a"))
    for row in validator.get("rows", []):
        log.info(
            "  validator   %-24s %-5s null=%s not_null=%s",
            row["attribute"], row["status"], row["null_count"], row["not_null_count"],
        )
