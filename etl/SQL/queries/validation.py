"""validator_fact_nulls: initialise, then check.

INIT_ROWS seeds one row per nullable fact attribute. Each CHECK query returns the
number of rows that violate that attribute's NULL rule; zero means 'pass'.
"""

from __future__ import annotations

from SQL.tables.star import FACT_NULLABLE_ATTRIBUTES

CLEAR = "DELETE FROM validator_fact_nulls;"

INSERT_EXPECTATION = """
INSERT INTO validator_fact_nulls (attribute, null_allowed, null_rule, status)
VALUES (%(attribute)s, true, %(null_rule)s, 'pending')
"""

INIT_ROWS = [
    {"attribute": attr, "null_rule": rule}
    for attr, rule in FACT_NULLABLE_ATTRIBUTES.items()
]

COUNT_NULL = "SELECT count(*) FROM fact_gpu_model_compatibility WHERE {col} IS NULL;"
COUNT_NOT_NULL = "SELECT count(*) FROM fact_gpu_model_compatibility WHERE {col} IS NOT NULL;"
COUNT_TOTAL = "SELECT count(*) FROM fact_gpu_model_compatibility;"

# Violation counts. XOR between "column is NULL" and "column should be NULL".
VIOLATIONS: dict[str, str] = {
    "model_vram_footprint_gb": """
        SELECT count(*)
        FROM fact_gpu_model_compatibility f
        JOIN dim_model m ON m.model_key = f.model_key
        WHERE (f.model_vram_footprint_gb IS NULL) <> (m.parameter_count IS NULL)
    """,
    "fits_in_vram": """
        SELECT count(*) FROM fact_gpu_model_compatibility
        WHERE (fits_in_vram IS NULL) <> (model_vram_footprint_gb IS NULL)
    """,
    "vram_headroom_gb": """
        SELECT count(*) FROM fact_gpu_model_compatibility
        WHERE (vram_headroom_gb IS NULL) <> (model_vram_footprint_gb IS NULL)
    """,
    "quantization_required": """
        SELECT count(*) FROM fact_gpu_model_compatibility
        WHERE (quantization_required IS NULL) <> (model_vram_footprint_gb IS NULL)
    """,
    "estimated_throughput": """
        SELECT count(*)
        FROM fact_gpu_model_compatibility f
        JOIN dim_model m ON m.model_key = f.model_key
        JOIN dim_gpu   g ON g.gpu_key   = f.gpu_key
        WHERE (f.estimated_throughput IS NULL)
              <> (NOT (m.is_generative
                       AND m.parameter_count IS NOT NULL
                       AND g.memory_bandwidth_gbs IS NOT NULL))
    """,
    "throughput_unit": """
        SELECT count(*) FROM fact_gpu_model_compatibility
        WHERE (throughput_unit IS NULL) <> (estimated_throughput IS NULL)
    """,
}

UPDATE_RESULT = """
UPDATE validator_fact_nulls
SET null_count = %(null_count)s,
    not_null_count = %(not_null_count)s,
    total_rows = %(total_rows)s,
    status = %(status)s,
    detail = %(detail)s,
    checked_at = now()
WHERE attribute = %(attribute)s
"""

SELECT_ALL = """
SELECT attribute, null_allowed, null_rule, null_count, not_null_count,
       total_rows, status, detail, checked_at
FROM validator_fact_nulls
ORDER BY attribute
"""

COUNT_FAILED = "SELECT count(*) FROM validator_fact_nulls WHERE status = 'fail';"
