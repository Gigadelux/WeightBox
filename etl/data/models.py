"""Pydantic models that cross a module boundary (phase to pipeline, DDL module
to SchemaValidator). Row data stays in pandas DataFrames; these are contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
#  Schema description (single source of truth for DDL *and* validation)
# --------------------------------------------------------------------------- #


class ColumnSpec(BaseModel):
    """One column. ``sql_type`` is the base type as reported by
    ``information_schema.columns.data_type`` (lower-case, no length).
    ``default``, ``unique``, ``references`` and ``identity`` shape DDL only;
    SchemaValidator checks name, base type and nullability."""

    name: str
    sql_type: str
    nullable: bool = True
    default: str | None = None
    unique: bool = False
    references: str | None = None  # e.g. "dim_gpu(gpu_key)"
    identity: bool = False  # GENERATED ALWAYS AS IDENTITY

    def ddl_fragment(self) -> str:
        parts = [self.name, self.sql_type]
        if self.identity:
            parts.append("GENERATED ALWAYS AS IDENTITY")
        elif not self.nullable:
            parts.append("NOT NULL")
        if self.default is not None:
            parts.append(f"DEFAULT {self.default}")
        if self.unique:
            parts.append("UNIQUE")
        if self.references is not None:
            parts.append(f"REFERENCES {self.references}")
        return " ".join(parts)

    def matches(self, information_schema_type: str) -> bool:
        got = information_schema_type.strip().lower()
        want = self.sql_type.strip().lower()
        # information_schema reports e.g. "character varying" for varchar,
        # "timestamp with time zone" for timestamptz, "integer" for int.
        aliases = {
            "text": {"text", "character varying", "varchar"},
            "varchar": {"character varying", "varchar", "text"},
            "int": {"integer"},
            "integer": {"integer"},
            "bigint": {"bigint"},
            "smallint": {"smallint"},
            "numeric": {"numeric", "decimal"},
            "boolean": {"boolean"},
            "date": {"date"},
            "timestamptz": {"timestamp with time zone"},
        }
        return got in aliases.get(want, {want})


class TableSpec(BaseModel):
    """A table definition. ``.ddl()`` renders CREATE TABLE; the same object is
    handed to :class:`SchemaValidator` to check the live database."""

    schema_name: str = "public"
    name: str
    columns: list[ColumnSpec]
    primary_key: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)  # raw constraint lines

    @property
    def qualified(self) -> str:
        return f"{self.schema_name}.{self.name}"

    def column(self, name: str) -> ColumnSpec | None:
        return next((c for c in self.columns if c.name == name), None)

    def insertable_columns(self) -> list[str]:
        """Column names a bulk load should supply (identity columns excluded)."""
        return [c.name for c in self.columns if not c.identity]

    def ddl(self, *, if_not_exists: bool = True) -> str:
        head = "CREATE TABLE " + ("IF NOT EXISTS " if if_not_exists else "")
        lines: list[str] = [f"    {col.ddl_fragment()}" for col in self.columns]
        if self.primary_key:
            lines.append(f"    PRIMARY KEY ({', '.join(self.primary_key)})")
        lines.extend(f"    {line}" for line in self.extra)
        body = ",\n".join(lines)
        return f"{head}{self.qualified} (\n{body}\n);"


# --------------------------------------------------------------------------- #
#  Phase results
# --------------------------------------------------------------------------- #


class OdsLoadResult(BaseModel):
    file_name: str
    sha256: str
    row_count: int
    skipped: bool  # True => identical file already in ODS, upload skipped


class FactNullExpectation(BaseModel):
    """One row of ``validator_fact_nulls`` at initialisation time."""

    attribute: str
    null_allowed: bool
    null_rule: str


class FactNullResult(FactNullExpectation):
    """Same row after the check step."""

    null_count: int
    not_null_count: int
    total_rows: int
    status: str  # 'pass' | 'fail'
    detail: str | None = None


class PhaseReport(BaseModel):
    phase: str
    ok: bool
    started_at: datetime
    finished_at: datetime
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


class HealthReport(BaseModel):
    healthy: bool
    postgres_version: str
    database_size_pretty: str
    active_connections: int
    row_counts: dict[str, int] = Field(default_factory=dict)
    index_present: dict[str, bool] = Field(default_factory=dict)
    materialized_view_rows: dict[str, int] = Field(default_factory=dict)
    validator_all_pass: bool = False
    notes: list[str] = Field(default_factory=list)


class PipelineReport(BaseModel):
    ok: bool
    phases: list[PhaseReport] = Field(default_factory=list)
    health: HealthReport | None = None
