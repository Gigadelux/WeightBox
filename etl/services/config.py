"""Runtime configuration. Every value comes from the environment (``.env`` in
local and compose runs); nothing is hard-coded."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # PostgreSQL connection parts, shared with the db container
    postgres_user: str = "weightbox_admin"
    postgres_password: str = "change_me"
    postgres_db: str = "weightbox"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # SQLAlchemy URL (psycopg v3), used as the pandas to SQL bridge
    database_url: str | None = None
    # Plain libpq DSN, used by the psycopg connection
    pg_dsn: str | None = None

    # ETL knobs
    etl_csv_models_path: Path = Path("/app/csv/notable_ai_models.csv")
    etl_csv_gpus_path: Path = Path("/app/csv/gpu_specs_v7.csv")
    etl_batch_size: int = 5000
    etl_skip_ods_if_loaded: bool = True
    etl_fail_fast: bool = True
    etl_log_level: str = "INFO"

    # If set, integration tests use this DB instead of spinning a container
    test_database_url: str | None = None

    @field_validator("pg_dsn")
    @classmethod
    def _dsn_is_libpq(cls, v: str | None) -> str | None:
        if v and "+psycopg" in v:
            return v.replace("postgresql+psycopg://", "postgresql://")
        return v

    @model_validator(mode="after")
    def _connection_urls(self) -> "Settings":
        # Compose supplies one set of connection parts. URL.create safely
        # escapes passwords containing @, :, /, %, etc. Explicit URLs remain
        # supported for non-Compose callers and the integration-test fixtures.
        url = URL.create(
            "postgresql+psycopg", username=self.postgres_user,
            password=self.postgres_password, host=self.postgres_host,
            port=self.postgres_port, database=self.postgres_db,
        )
        if not self.database_url:
            self.database_url = url.render_as_string(hide_password=False)
        if not self.pg_dsn:
            self.pg_dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
        return self

    @property
    def sqlalchemy_url(self) -> str:
        assert self.database_url is not None
        return self.database_url

    def with_pg_dsn(self, dsn: str) -> "Settings":
        """Return a copy pointed at another database (used by tests)."""
        data = self.model_dump()
        data["pg_dsn"] = dsn.replace("postgresql+psycopg://", "postgresql://")
        data["database_url"] = (
            dsn
            if dsn.startswith("postgresql+psycopg://")
            else dsn.replace("postgresql://", "postgresql+psycopg://")
        )
        return Settings(**data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
