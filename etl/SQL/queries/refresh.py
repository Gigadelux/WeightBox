"""Materialized view refresh, run at the end of Phase 2."""

from __future__ import annotations

from SQL.tables.views import VIEW_DDL


def refresh_statements() -> list[str]:
    return [f"REFRESH MATERIALIZED VIEW {name};" for name in VIEW_DDL]


ANALYZE = "ANALYZE;"
