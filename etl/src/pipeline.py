"""Pipeline orchestrator.

Owns one PostgresConnector and runs the four phases in order:
initialization, etl, indexing, health. ``--only`` runs one phase; ``--from``
starts at a phase and runs to the end.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from data.models import PhaseReport, PipelineReport
from services.config import Settings
from services.postgres import PostgresConnector
from src import phase_etl, phase_health, phase_indexing, phase_initialization

log = logging.getLogger("weightbox.etl.pipeline")

PHASES = [
    ("initialization", phase_initialization.run),
    ("etl", phase_etl.run),
    ("indexing", phase_indexing.run),
    ("health", phase_health.run),
]
PHASE_NAMES = [name for name, _ in PHASES]


class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = PostgresConnector(settings)

    def close(self) -> None:
        self.db.close()

    def _selected(self, only: str | None, start_from: str | None) -> list[tuple[str, object]]:
        if only:
            return [p for p in PHASES if p[0] == only]
        if start_from:
            idx = PHASE_NAMES.index(start_from)
            return PHASES[idx:]
        return PHASES

    def run(self, *, only: str | None = None, start_from: str | None = None) -> PipelineReport:
        selected = self._selected(only, start_from)
        reports: list[PhaseReport] = []
        ok = True

        for name, fn in selected:
            log.info("phase %s: start", name)
            try:
                report = fn(self.db, self.settings)
            except Exception as exc:  # noqa: BLE001
                log.exception("phase %s: raised", name)
                now = datetime.now(timezone.utc)
                report = PhaseReport(
                    phase=name, ok=False, started_at=now, finished_at=now,
                    errors=[f"{type(exc).__name__}: {exc}"],
                )
            reports.append(report)
            log.info(
                "phase %s: %s in %.1fs", name, "ok" if report.ok else "FAILED", report.duration_s
            )
            if not report.ok:
                ok = False
                if self.settings.etl_fail_fast:
                    break

        health = next(
            (r.metrics.get("health") for r in reports if r.phase == "health" and r.metrics),
            None,
        )
        return PipelineReport(
            ok=ok,
            phases=reports,
            health=health if health else None,
        )
