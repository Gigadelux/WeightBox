"""Phase 1: create every relation, verify the schema, load the CSVs into the ODS.

The ODS load is idempotent: an unchanged file (matching sha256 already in
``ods.load_audit``) is skipped when ``ETL_SKIP_ODS_IF_LOADED`` is set.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

import pandas as pd

from data.models import OdsLoadResult, PhaseReport
from services.config import Settings
from services.postgres import PostgresConnector
from services.schema_validator import SchemaValidator
from SQL.tables import ALL_TABLE_SPECS, MATERIALIZED_VIEW_NAMES, bootstrap_ddl
from SQL.tables import ods as ods_tables
from SQL.queries import ods_load

log = logging.getLogger("weightbox.etl.phase1")

_FILES = [
    ("ods_models", "notable_ai_models.csv", ods_tables.ODS_MODELS, ods_tables.ODS_MODELS_COLUMNS),
    ("ods_gpus", "gpu_specs_v7.csv", ods_tables.ODS_GPUS, ods_tables.ODS_GPUS_COLUMNS),
]


def run(db: PostgresConnector, settings: Settings) -> PhaseReport:
    started = datetime.now(timezone.utc)
    errors: list[str] = []
    metrics: dict[str, object] = {}

    db.execute_script(bootstrap_ddl())
    metrics["relations_created"] = len(ALL_TABLE_SPECS) + len(MATERIALIZED_VIEW_NAMES)

    validator = SchemaValidator(db)
    validator.check_schema(ALL_TABLE_SPECS, MATERIALIZED_VIEW_NAMES, strict=True)
    metrics["schema_ok"] = True

    paths = {
        "ods_models": settings.etl_csv_models_path,
        "ods_gpus": settings.etl_csv_gpus_path,
    }
    loads: list[OdsLoadResult] = []
    for ods_table, expected_name, spec, columns in _FILES:
        path = paths[ods_table]
        if not path.exists():
            raise FileNotFoundError(f"source CSV not found: {path}")
        sha = _sha256(path)

        already = int(
            db.fetch_scalar(ods_load.ALREADY_LOADED, {"ods_table": ods_table, "sha256": sha}) or 0
        )
        current_rows = db.row_count("ods", ods_table)
        if settings.etl_skip_ods_if_loaded and already > 0 and current_rows > 0:
            log.info("%s already holds %s (sha match), skipping upload", ods_table, path.name)
            loads.append(OdsLoadResult(file_name=expected_name, sha256=sha, row_count=current_rows, skipped=True))
            continue

        frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        got = [ods_tables.slugify(c) for c in frame.columns]
        if got != columns:
            raise ValueError(
                f"{path.name}: header mismatch.\n expected {columns}\n got      {got}"
            )
        frame.columns = columns
        frame["_source_sha256"] = sha

        db.execute(ods_load.truncate("ods", ods_table))
        n = db.copy_df(
            frame,
            schema="ods",
            table=ods_table,
            columns=[*columns, "_source_sha256"],
        )
        db.execute(
            ods_load.INSERT_LOAD_AUDIT,
            {"ods_table": ods_table, "file_name": expected_name, "sha256": sha, "row_count": n},
        )
        _write_profile(db, ods_table, frame, columns)
        log.info("loaded %s rows into ods.%s from %s", n, ods_table, path.name)
        loads.append(OdsLoadResult(file_name=expected_name, sha256=sha, row_count=n, skipped=False))

    metrics["ods_loads"] = [x.model_dump() for x in loads]
    finished = datetime.now(timezone.utc)
    return PhaseReport(
        phase="initialization",
        ok=not errors,
        started_at=started,
        finished_at=finished,
        metrics=metrics,
        errors=errors,
    )


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_profile(db: PostgresConnector, ods_table: str, frame: pd.DataFrame, columns: list[str]) -> None:
    total = len(frame)
    rows = []
    for col in columns:
        empty = int((frame[col].astype(str).str.strip() == "").sum())
        rows.append(
            {
                "ods_table": ods_table,
                "column_name": col,
                "total_rows": total,
                "empty_count": empty,
                "empty_rate": round(empty / total, 4) if total else 0.0,
            }
        )
    db.execute("DELETE FROM ods.profile_log WHERE ods_table = %s", (ods_table,))
    with db.transaction() as conn, conn.cursor() as cur:
        cur.executemany(ods_load.INSERT_PROFILE_ROW, rows)
