"""DDL for every WeightBox relation. ``ALL_TABLE_SPECS`` drives both the CREATE
step in Phase 1 and SchemaValidator. ``bootstrap_ddl()`` returns the full ordered
script: schema, then ODS, star, validator, then the materialized views."""

from __future__ import annotations

from data.models import TableSpec

from SQL.tables import ods, star, validator, views

# Order matters: FK targets before the fact, tables before the views over them.
ALL_TABLE_SPECS: list[TableSpec] = [
    *ods.TABLE_SPECS,
    star.DIM_MODEL,
    star.DIM_GPU,
    star.FACT,
    validator.VALIDATOR_FACT_NULLS,
]

# Relations checked for mere existence (not column-by-column): the MVs.
MATERIALIZED_VIEW_NAMES: list[str] = list(views.VIEW_DDL.keys())


def bootstrap_ddl() -> str:
    """Idempotent DDL for the whole warehouse, safe to run on every start."""
    parts: list[str] = [ods.CREATE_SCHEMA]
    parts += [spec.ddl(if_not_exists=True) for spec in ALL_TABLE_SPECS]
    parts += list(views.VIEW_DDL.values())
    return "\n\n".join(parts) + "\n"


__all__ = [
    "ALL_TABLE_SPECS",
    "MATERIALIZED_VIEW_NAMES",
    "bootstrap_ddl",
    "ods",
    "star",
    "validator",
    "views",
]
