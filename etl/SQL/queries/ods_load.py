"""Statements for Phase 1: ODS load audit, column profiling, idempotency check."""

from __future__ import annotations

ALREADY_LOADED = """
SELECT count(*) AS n
FROM ods.load_audit
WHERE ods_table = %(ods_table)s AND sha256 = %(sha256)s
"""

INSERT_LOAD_AUDIT = """
INSERT INTO ods.load_audit (ods_table, file_name, sha256, row_count)
VALUES (%(ods_table)s, %(file_name)s, %(sha256)s, %(row_count)s)
"""

INSERT_PROFILE_ROW = """
INSERT INTO ods.profile_log (ods_table, column_name, total_rows, empty_count, empty_rate)
VALUES (%(ods_table)s, %(column_name)s, %(total_rows)s, %(empty_count)s, %(empty_rate)s)
"""


def truncate(schema: str, table: str) -> str:
    return f"TRUNCATE {schema}.{table} RESTART IDENTITY;"
