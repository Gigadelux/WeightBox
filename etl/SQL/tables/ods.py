"""ODS layer: verbatim all-text mirrors of the two source CSVs, plus load-audit,
profiling and reject bookkeeping.

The canonical CSV header lists live here so Phase 1 can create the ODS tables
before the CSV is opened. The loader re-slugifies the real headers and asserts
they match ``ODS_*_COLUMNS``, so a changed CSV fails loudly rather than dropping
columns silently.
"""

from __future__ import annotations

import re

from data.models import ColumnSpec, TableSpec

SCHEMA = "ods"
CREATE_SCHEMA = f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};"

# --------------------------------------------------------------------------- #
#  header -> column-name slug
# --------------------------------------------------------------------------- #


def slugify(header: str) -> str:
    """``"Training compute (FLOP)"`` -> ``training_compute_flop``;
    ``"productName"`` -> ``product_name``."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", header.strip())  # split camelCase
    s = s.lower()
    s = re.sub(r"[^\w]+", "_", s)  # non-word -> _
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# Exact header order of csv/notable_ai_models.csv (47 columns).
MODEL_CSV_HEADERS: list[str] = [
    "Model", "Organization", "Publication date", "Domain", "Task", "Parameters",
    "Parameters notes", "Training compute (FLOP)", "Training compute notes",
    "Training dataset", "Training dataset size (total)", "Dataset size notes",
    "Confidence", "Link", "Reference", "Citations", "Authors", "Abstract",
    "Organization categorization", "Country (of organization)",
    "Notability criteria", "Notability criteria notes", "Epochs",
    "Training time (hours)", "Training time notes", "Training hardware",
    "Hardware quantity", "Hardware utilization (MFU)",
    "Training compute cost (2023 USD)", "Compute cost notes",
    "Training power draw (W)", "Base model", "Finetune compute (FLOP)",
    "Finetune compute notes", "Batch size", "Batch size notes",
    "Model accessibility", "Training code accessibility",
    "Inference code accessibility", "Accessibility notes", "Numerical format",
    "Frontier model", "Hardware acquisition cost", "Hardware utilization (HFU)",
    "Training compute cost (cloud)", "Training compute cost (upfront)",
    "Open model weights?",
]

# Exact header order of csv/gpu_specs_v7.csv (16 columns; BOM stripped upstream).
GPU_CSV_HEADERS: list[str] = [
    "manufacturer", "productName", "releaseYear", "memSize", "memBusWidth",
    "gpuClock", "memClock", "unifiedShader", "tmu", "rop", "pixelShader",
    "vertexShader", "igp", "bus", "memType", "gpuChip",
]

ODS_MODELS_COLUMNS: list[str] = [slugify(h) for h in MODEL_CSV_HEADERS]
ODS_GPUS_COLUMNS: list[str] = [slugify(h) for h in GPU_CSV_HEADERS]

assert len(set(ODS_MODELS_COLUMNS)) == len(ODS_MODELS_COLUMNS), "model slug clash"
assert len(set(ODS_GPUS_COLUMNS)) == len(ODS_GPUS_COLUMNS), "gpu slug clash"

HEADER_TO_COLUMN: dict[str, str] = {
    **{h: slugify(h) for h in MODEL_CSV_HEADERS},
    **{h: slugify(h) for h in GPU_CSV_HEADERS},
}

# --------------------------------------------------------------------------- #
#  table specs
# --------------------------------------------------------------------------- #


def _text_cols(names: list[str]) -> list[ColumnSpec]:
    return [ColumnSpec(name=n, sql_type="text", nullable=True) for n in names]


_AUDIT_TAIL = [
    ColumnSpec(name="_source_sha256", sql_type="text", nullable=False),
    ColumnSpec(name="_loaded_at", sql_type="timestamptz", nullable=False, default="now()"),
]

ODS_MODELS = TableSpec(
    schema_name=SCHEMA,
    name="ods_models",
    columns=[
        ColumnSpec(name="ods_model_id", sql_type="bigint", nullable=False, identity=True),
        *_text_cols(ODS_MODELS_COLUMNS),
        *_AUDIT_TAIL,
    ],
    primary_key=["ods_model_id"],
)

ODS_GPUS = TableSpec(
    schema_name=SCHEMA,
    name="ods_gpus",
    columns=[
        ColumnSpec(name="ods_gpu_id", sql_type="bigint", nullable=False, identity=True),
        *_text_cols(ODS_GPUS_COLUMNS),
        *_AUDIT_TAIL,
    ],
    primary_key=["ods_gpu_id"],
)

LOAD_AUDIT = TableSpec(
    schema_name=SCHEMA,
    name="load_audit",
    columns=[
        ColumnSpec(name="load_id", sql_type="bigint", nullable=False, identity=True),
        ColumnSpec(name="ods_table", sql_type="text", nullable=False),
        ColumnSpec(name="file_name", sql_type="text", nullable=False),
        ColumnSpec(name="sha256", sql_type="text", nullable=False),
        ColumnSpec(name="row_count", sql_type="integer", nullable=False),
        ColumnSpec(name="loaded_at", sql_type="timestamptz", nullable=False, default="now()"),
    ],
    primary_key=["load_id"],
)

PROFILE_LOG = TableSpec(
    schema_name=SCHEMA,
    name="profile_log",
    columns=[
        ColumnSpec(name="profile_id", sql_type="bigint", nullable=False, identity=True),
        ColumnSpec(name="ods_table", sql_type="text", nullable=False),
        ColumnSpec(name="column_name", sql_type="text", nullable=False),
        ColumnSpec(name="total_rows", sql_type="integer", nullable=False),
        ColumnSpec(name="empty_count", sql_type="integer", nullable=False),
        ColumnSpec(name="empty_rate", sql_type="numeric", nullable=False),
        ColumnSpec(name="profiled_at", sql_type="timestamptz", nullable=False, default="now()"),
    ],
    primary_key=["profile_id"],
)


def _reject_spec(name: str) -> TableSpec:
    return TableSpec(
        schema_name=SCHEMA,
        name=name,
        columns=[
            ColumnSpec(name="reject_id", sql_type="bigint", nullable=False, identity=True),
            ColumnSpec(name="natural_key", sql_type="text", nullable=True),
            ColumnSpec(name="rule", sql_type="text", nullable=False),
            ColumnSpec(name="detail", sql_type="text", nullable=True),
            ColumnSpec(name="rejected_at", sql_type="timestamptz", nullable=False, default="now()"),
        ],
        primary_key=["reject_id"],
    )


REJECT_MODELS = _reject_spec("reject_models")
REJECT_GPUS = _reject_spec("reject_gpus")

TABLE_SPECS: list[TableSpec] = [
    ODS_MODELS,
    ODS_GPUS,
    LOAD_AUDIT,
    PROFILE_LOG,
    REJECT_MODELS,
    REJECT_GPUS,
]
