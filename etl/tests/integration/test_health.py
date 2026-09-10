from __future__ import annotations

import pytest

from src import phase_health

pytestmark = pytest.mark.integration


def test_health_phase_reports_healthy_after_a_run(ran, settings, db):
    report = phase_health.run(db, settings)
    assert report.ok is True
    health = report.metrics["health"]
    assert health["healthy"] is True
    assert health["validator_all_pass"] is True
    assert health["row_counts"]["public.fact_gpu_model_compatibility"] > 0
    assert all(health["index_present"].values())


def test_pipeline_report_carries_health(ran):
    assert ran.health is not None
    assert ran.health.healthy is True
