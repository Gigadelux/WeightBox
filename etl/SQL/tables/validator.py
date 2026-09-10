"""validator_fact_nulls: one row per nullable fact attribute.

Initialised at fact load (status 'pending'), then filled and graded by the check
step. Any 'fail' row aborts the pipeline when ETL_FAIL_FAST is set.
"""

from __future__ import annotations

from data.models import ColumnSpec, TableSpec

VALIDATOR_FACT_NULLS = TableSpec(
    schema_name="public",
    name="validator_fact_nulls",
    columns=[
        ColumnSpec(name="attribute", sql_type="text", nullable=False),
        ColumnSpec(name="null_allowed", sql_type="boolean", nullable=False),
        ColumnSpec(name="null_rule", sql_type="text", nullable=False),
        ColumnSpec(name="null_count", sql_type="bigint", nullable=True),
        ColumnSpec(name="not_null_count", sql_type="bigint", nullable=True),
        ColumnSpec(name="total_rows", sql_type="bigint", nullable=True),
        ColumnSpec(name="status", sql_type="text", nullable=False, default="'pending'"),
        ColumnSpec(name="detail", sql_type="text", nullable=True),
        ColumnSpec(name="checked_at", sql_type="timestamptz", nullable=True),
    ],
    primary_key=["attribute"],
)
