from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.config import Settings
from services.postgres import PostgresConnector


def _container_url() -> str | None:
    """Start a throwaway Postgres if Docker and testcontainers are available."""
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception:
        return None
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception:
        return None
    pytest._wb_container = container  # keep a reference alive for the session
    return container.get_connection_url()


@pytest.fixture(scope="session")
def pg_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or _container_url()
    if not url:
        pytest.skip("no TEST_DATABASE_URL and testcontainers/Docker unavailable")
    return url.replace("postgresql+psycopg2://", "postgresql://")


@pytest.fixture()
def settings(pg_url: str, tmp_path: Path) -> Settings:
    from tests._fixtures import write_fixture_csvs

    models_csv, gpus_csv = write_fixture_csvs(tmp_path / "csv")
    base = Settings(
        etl_csv_models_path=models_csv,
        etl_csv_gpus_path=gpus_csv,
        etl_fail_fast=True,
    )
    return base.with_pg_dsn(pg_url)


@pytest.fixture()
def db(settings: Settings):
    connector = PostgresConnector(settings)
    try:
        yield connector
    finally:
        connector.close()


def reset_database(connector: PostgresConnector) -> None:
    connector.execute_script(
        """
        DROP SCHEMA IF EXISTS ods CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS mv_deployability_by_year_arch CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS mv_gpu_generation_tradeoff CASCADE;
        DROP MATERIALIZED VIEW IF EXISTS mv_domain_accessibility CASCADE;
        DROP TABLE IF EXISTS fact_gpu_model_compatibility CASCADE;
        DROP TABLE IF EXISTS validator_fact_nulls CASCADE;
        DROP TABLE IF EXISTS dim_model CASCADE;
        DROP TABLE IF EXISTS dim_gpu CASCADE;
        """
    )


@pytest.fixture()
def ran(settings: Settings, db: PostgresConnector):
    """A clean database with a full successful pipeline run behind it."""
    from src.pipeline import Pipeline

    reset_database(db)
    pipe = Pipeline(settings)
    try:
        report = pipe.run()
    finally:
        pipe.close()
    assert report.ok, report.model_dump()
    return report
