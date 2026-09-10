"""Phase 3: create the fact indexes (and the supporting ones), then verify.

The two required indexes are ``ix_fact_model_nk`` and ``ix_fact_gpu_nk`` on the
single fact table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from data.models import PhaseReport
from services.config import Settings
from services.postgres import PostgresConnector
from SQL.tables.indexes import ALL_INDEXES, FACT_NAME_INDEXES

log = logging.getLogger("weightbox.etl.phase3")


def run(db: PostgresConnector, settings: Settings) -> PhaseReport:  # noqa: ARG001
    started = datetime.now(timezone.utc)

    for name, stmt in ALL_INDEXES.items():
        db.execute(stmt)
        log.info("index ready: %s", name)
    db.execute("ANALYZE fact_gpu_model_compatibility;")

    present = {name: db.index_exists(name) for name in FACT_NAME_INDEXES}
    missing = [name for name, ok in present.items() if not ok]
    if missing:
        raise RuntimeError(f"required fact indexes missing after creation: {missing}")

    finished = datetime.now(timezone.utc)
    return PhaseReport(
        phase="indexing",
        ok=True,
        started_at=started,
        finished_at=finished,
        metrics={
            "indexes_created": len(ALL_INDEXES),
            "fact_name_indexes_present": present,
        },
    )
