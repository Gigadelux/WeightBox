"""ROLAP star schema: two dimensions and one fact.

No dim_time: the calendar hierarchy is inlined on dim_model (WEIGHTBOX_SPECS.md
section 2.5). The fact carries denormalised model_nk / gpu_nk so name-filtered
scans do not need a dimension join.
"""

from __future__ import annotations

from data.models import ColumnSpec, TableSpec

SCHEMA = "public"

DIM_MODEL = TableSpec(
    schema_name=SCHEMA,
    name="dim_model",
    columns=[
        ColumnSpec(name="model_key", sql_type="bigint", nullable=False, identity=True),
        ColumnSpec(name="model_nk", sql_type="text", nullable=False, unique=True),
        ColumnSpec(name="model_name", sql_type="text", nullable=False),
        ColumnSpec(name="organization", sql_type="text", nullable=False, default="'Unknown'"),
        ColumnSpec(name="organization_country", sql_type="text", nullable=False, default="'Unknown'"),
        ColumnSpec(name="primary_domain", sql_type="text", nullable=False),
        ColumnSpec(name="is_generative", sql_type="boolean", nullable=False),
        ColumnSpec(name="throughput_unit", sql_type="text", nullable=True),
        ColumnSpec(name="parameter_count", sql_type="numeric", nullable=True),
        ColumnSpec(name="parameter_count_is_estimated", sql_type="boolean", nullable=False, default="false"),
        ColumnSpec(name="parameter_bucket", sql_type="text", nullable=False),
        ColumnSpec(name="training_compute_flop", sql_type="numeric", nullable=True),
        ColumnSpec(name="release_date", sql_type="date", nullable=False),
        ColumnSpec(name="release_month", sql_type="smallint", nullable=False),
        ColumnSpec(name="release_quarter", sql_type="smallint", nullable=False),
        ColumnSpec(name="release_year", sql_type="smallint", nullable=False),
        ColumnSpec(name="release_decade", sql_type="smallint", nullable=False),
        ColumnSpec(name="confidence", sql_type="text", nullable=True),
        ColumnSpec(name="source_dataset", sql_type="text", nullable=False, default="'notable_ai_models'"),
    ],
    primary_key=["model_key"],
)

DIM_GPU = TableSpec(
    schema_name=SCHEMA,
    name="dim_gpu",
    columns=[
        ColumnSpec(name="gpu_key", sql_type="bigint", nullable=False, identity=True),
        ColumnSpec(name="gpu_nk", sql_type="text", nullable=False, unique=True),
        ColumnSpec(name="product_name", sql_type="text", nullable=False),
        ColumnSpec(name="manufacturer", sql_type="text", nullable=False),
        ColumnSpec(name="gpu_chip", sql_type="text", nullable=True),
        ColumnSpec(name="gpu_architecture", sql_type="text", nullable=False, default="'Unknown'"),
        ColumnSpec(name="release_year", sql_type="smallint", nullable=True),
        ColumnSpec(name="vram_gb", sql_type="numeric", nullable=False),
        ColumnSpec(name="vram_bucket", sql_type="text", nullable=False),
        ColumnSpec(name="mem_bus_width_bit", sql_type="integer", nullable=True),
        ColumnSpec(name="mem_clock_mhz", sql_type="numeric", nullable=True),
        ColumnSpec(name="mem_type", sql_type="text", nullable=False),
        ColumnSpec(name="mem_family", sql_type="text", nullable=False),
        ColumnSpec(name="data_rate", sql_type="numeric", nullable=False),
        ColumnSpec(name="memory_bandwidth_gbs", sql_type="numeric", nullable=False),
        ColumnSpec(name="bandwidth_is_estimated", sql_type="boolean", nullable=False, default="false"),
        ColumnSpec(name="specs_suspect", sql_type="boolean", nullable=False, default="false"),
    ],
    primary_key=["gpu_key"],
)

FACT = TableSpec(
    schema_name=SCHEMA,
    name="fact_gpu_model_compatibility",
    columns=[
        ColumnSpec(name="gpu_key", sql_type="bigint", nullable=False, references="dim_gpu(gpu_key)"),
        ColumnSpec(name="model_key", sql_type="bigint", nullable=False, references="dim_model(model_key)"),
        ColumnSpec(name="model_nk", sql_type="text", nullable=False),
        ColumnSpec(name="gpu_nk", sql_type="text", nullable=False),
        ColumnSpec(name="model_vram_footprint_gb", sql_type="numeric", nullable=True),
        ColumnSpec(name="fits_in_vram", sql_type="boolean", nullable=True),
        ColumnSpec(name="vram_headroom_gb", sql_type="numeric", nullable=True),
        ColumnSpec(name="quantization_required", sql_type="text", nullable=True),
        ColumnSpec(name="estimated_throughput", sql_type="numeric", nullable=True),
        ColumnSpec(name="throughput_unit", sql_type="varchar", nullable=True),
    ],
    primary_key=["gpu_key", "model_key"],
)

# Nullable fact attributes tracked by validator_fact_nulls, with the rule each
# NULL must satisfy. Consumed by SQL.queries.validation.
FACT_NULLABLE_ATTRIBUTES: dict[str, str] = {
    "model_vram_footprint_gb": "NULL if and only if dim_model.parameter_count is NULL",
    "fits_in_vram": "NULL if and only if model_vram_footprint_gb is NULL",
    "vram_headroom_gb": "NULL if and only if model_vram_footprint_gb is NULL",
    "quantization_required": "NULL if and only if model_vram_footprint_gb is NULL",
    "estimated_throughput": "NULL unless is_generative and parameter_count and bandwidth are all present",
    "throughput_unit": "NULL if and only if estimated_throughput is NULL",
}
