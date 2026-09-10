"""Phase 4: a short read of the Postgres instance and the loaded warehouse."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from data.models import HealthReport, PhaseReport
from services.config import Settings
from services.postgres import PostgresConnector
from SQL.queries import health

log = logging.getLogger("weightbox.etl.phase4")

_MUST_BE_NONEMPTY = {
    ("public", "dim_model"),
    ("public", "dim_gpu"),
    ("public", "fact_gpu_model_compatibility"),
    ("public", "validator_fact_nulls"),
}


def run(db: PostgresConnector, settings: Settings) -> PhaseReport:  # noqa: ARG001
    started = datetime.now(timezone.utc)

    version = str(db.fetch_scalar(health.VERSION) or "")
    size = str(db.fetch_scalar(health.DATABASE_SIZE_PRETTY) or "")
    conns = int(db.fetch_scalar(health.ACTIVE_CONNECTIONS) or 0)
    validator_ok = bool(db.fetch_scalar(health.VALIDATOR_ALL_PASS))

    row_counts = {
        f"{schema}.{table}": db.row_count(schema, table)
        for schema, table in health.ROW_COUNT_TARGETS
    }
    index_present = {name: db.index_exists(name) for name in health.INDEX_TARGETS}
    mv_rows = {
        name: db.row_count("public", name)
        for name in ("mv_deployability_by_year_arch", "mv_gpu_generation_tradeoff",
                     "mv_domain_accessibility")
    }

    notes: list[str] = []
    for schema, table in _MUST_BE_NONEMPTY:
        if row_counts.get(f"{schema}.{table}", 0) == 0:
            notes.append(f"{schema}.{table} is empty")
    for name, ok in index_present.items():
        if not ok:
            notes.append(f"index {name} missing")
    if not validator_ok:
        notes.append("validator_fact_nulls has non-pass rows")

    report = HealthReport(
        healthy=not notes,
        postgres_version=version.split(",")[0],
        database_size_pretty=size,
        active_connections=conns,
        row_counts=row_counts,
        index_present=index_present,
        materialized_view_rows=mv_rows,
        validator_all_pass=validator_ok,
        notes=notes,
    )
    for line in _format(report):
        log.info(line)

    finished = datetime.now(timezone.utc)
    return PhaseReport(
        phase="health",
        ok=report.healthy,
        started_at=started,
        finished_at=finished,
        metrics={"health": report.model_dump()},
    )


def _format(r: HealthReport) -> list[str]:
    out = [
        f"postgres:   {r.postgres_version}",
        f"db size:    {r.database_size_pretty}",
        f"conns:      {r.active_connections}",
        f"validator:  {'all pass' if r.validator_all_pass else 'FAIL'}",
    ]
    out += [f"rows {k:40s} {v}" for k, v in r.row_counts.items()]
    out += [f"mv   {k:40s} {v}" for k, v in r.materialized_view_rows.items()]
    if r.notes:
        out.append("notes: " + "; ".join(r.notes))
    return out
