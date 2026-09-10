"""Schema and data-health checks.

Two jobs:

1. ``check_schema`` confirms every expected relation exists and, for tables, that
   the live columns match the TableSpec that created them (name, base type,
   nullability). Drift raises before any data is touched.
2. ``initialize_fact_null_validator`` / ``check_fact_null_validator`` drive the
   ``validator_fact_nulls`` table: seed one row per nullable fact attribute, then
   grade each against its NULL rule after the fact load.
"""

from __future__ import annotations

import logging

from data.models import FactNullResult, TableSpec
from services.postgres import PostgresConnector
from SQL.queries import validation

log = logging.getLogger("weightbox.etl.schema_validator")


class SchemaError(RuntimeError):
    pass


class SchemaValidator:
    def __init__(self, db: PostgresConnector):
        self.db = db

    def check_schema(
        self, specs: list[TableSpec], mv_names: list[str], *, strict: bool = True
    ) -> list[str]:
        problems: list[str] = []

        for name in mv_names:
            if not self.db.relation_exists("public", name):
                problems.append(f"missing materialized view: {name}")

        for spec in specs:
            if not self.db.table_exists(spec.schema_name, spec.name):
                problems.append(f"missing table: {spec.qualified}")
                continue
            live = self.db.columns(spec.schema_name, spec.name)
            for col in spec.columns:
                got = live.get(col.name)
                if got is None:
                    problems.append(f"{spec.qualified}: missing column {col.name}")
                    continue
                if not col.matches(got["data_type"]):
                    problems.append(
                        f"{spec.qualified}.{col.name}: type is {got['data_type']!r}, "
                        f"spec wants {col.sql_type!r}"
                    )
                if got["nullable"] != col.nullable:
                    problems.append(
                        f"{spec.qualified}.{col.name}: nullable={got['nullable']}, "
                        f"spec wants nullable={col.nullable}"
                    )

        if problems and strict:
            raise SchemaError("; ".join(problems))
        return problems

    def initialize_fact_null_validator(self) -> int:
        with self.db.transaction() as conn, conn.cursor() as cur:
            cur.execute(validation.CLEAR)
            cur.executemany(validation.INSERT_EXPECTATION, validation.INIT_ROWS)
        log.info("validator_fact_nulls seeded with %d rows", len(validation.INIT_ROWS))
        return len(validation.INIT_ROWS)

    def check_fact_null_validator(self) -> list[FactNullResult]:
        results: list[FactNullResult] = []
        total = int(self.db.fetch_scalar(validation.COUNT_TOTAL) or 0)

        for row in self.db.fetch_all(validation.SELECT_ALL):
            attr = row["attribute"]
            null_count = int(
                self.db.fetch_scalar(validation.COUNT_NULL.format(col=attr)) or 0
            )
            not_null_count = int(
                self.db.fetch_scalar(validation.COUNT_NOT_NULL.format(col=attr)) or 0
            )
            violations = int(
                self.db.fetch_scalar(validation.VIOLATIONS[attr]) or 0
            )
            status = "pass" if violations == 0 else "fail"
            detail = None if violations == 0 else f"{violations} rows break the NULL rule"

            self.db.execute(
                validation.UPDATE_RESULT,
                {
                    "attribute": attr,
                    "null_count": null_count,
                    "not_null_count": not_null_count,
                    "total_rows": total,
                    "status": status,
                    "detail": detail,
                },
            )
            results.append(
                FactNullResult(
                    attribute=attr,
                    null_allowed=row["null_allowed"],
                    null_rule=row["null_rule"],
                    null_count=null_count,
                    not_null_count=not_null_count,
                    total_rows=total,
                    status=status,
                    detail=detail,
                )
            )
        return results
