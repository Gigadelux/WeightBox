# WeightBox: Data Warehouse Design Specification

**GPU and Model Compatibility Observatory**
Data Management 2025/2026, ROLAP data warehouse (PostgreSQL)
Marco De Luca (2283822) · Chrision Wynaar (2237431)

> This document is the design authority for the data warehouse. It follows the
> course methodology (Golfarelli & Rizzi, *Data Warehouse Design: Modern
> Principles and Methodologies*, McGraw-Hill 2009; `docs/lessons/DataWarehousing.pdf`):
> requirement analysis → conceptual design (Dimensional Fact Model) → logical
> design (ROLAP star schema) → ETL (Extraction / Cleansing / Transformation /
> Loading) → view materialization → optimization.
>
> Scope of this document: the **data warehouse only** (ODS load, star schema, ETL,
> OLAP layer). The Next.js frontend, whose server components query the star
> schema and materialized views **directly over a PostgreSQL connection, with no
> intermediate API service**, is out of scope here.

---

## Table of contents

1. [Introduction & business question](#1-introduction--business-question)
2. [Requirement analysis](#2-requirement-analysis)
3. [Conceptual design: Dimensional Fact Model](#3-conceptual-design-dimensional-fact-model)
4. [Logical design: ROLAP star schema](#4-logical-design-rolap-star-schema)
5. [Derived-attribute computation](#5-derived-attribute-computation)
6. [ETL pipeline](#6-etl-pipeline)
7. [OLAP layer: queries & materialized views](#7-olap-layer-queries--materialized-views)
8. [Physical optimization](#8-physical-optimization)
9. [Appendices](#9-appendices)

---

## 1. Introduction & business question

**Business question.** *Given a specific GPU, which AI models can it realistically
run, at what inference speed, and under what conditions?* This is the deployment
feasibility problem a company faces when evaluating on-premise AI adoption without
relying on cloud infrastructure.

The warehouse answers it by materialising, for every `(GPU, model)` pair, whether
the model's weights **fit in the card's VRAM**, how much **headroom** is left,
whether **quantization** is required to make it fit, and, for generative models,
an **estimated inference throughput** derived from the card's memory bandwidth.

**Architecture.** Two-layer ROLAP (per the lecture's "Two-Layer Architecture"),
with an **ODS (Operational Data Store)** staging tier: each source CSV is first
loaded *unmodified* into an ODS table (`ODS_MODELS`, `ODS_GPUS`); a single
one-time ETL script then reads only from those tables to build the star schema.

```
 source layer          ODS layer (raw 1:1 load)      data-warehouse layer (star)
┌───────────────┐   ┌──────────────────────────┐   ┌────────────────────────┐
│ csv/          │   │ ods.ods_models (all-text)│   │ dim_model  dim_gpu     │
│  notable_ai_  │──▶│ ods.ods_gpus   (all-text)│──▶│  (calendar hierarchy   │
│  models.csv   │   │                          │   │   inlined on dim_model)│
│ csv/gpu_      │   │  one-time ETL script:     │   │ fact_gpu_model_        │
│  specs_v7.csv │   │  cleanse → transform →    │   │   compatibility        │
└───────────────┘   │  load; reject tables     │   │ mv_* materialized views│
                    │                          │   └───────────┬────────────┘
                    └──────────────────────────┘               │
                                                   Next.js server components
                                                   (direct SQL, no API tier)
```

Everything runs locally via Docker Compose: a PostgreSQL container hosts both the
ODS and the warehouse, a one-shot Python ETL container performs the two-pass load
(raw CSV → ODS tables, then ODS → star schema, **Refresh** mode), and the Next.js
application queries the star schema and materialized views directly over a
PostgreSQL connection, **there is no separate API service**. No cloud
dependencies.

**Note on the source data.** The proposal (`docs/DBMS Project .pdf`) quotes
"~3,500 models" and "~500 GPUs"; the CSVs actually in the repo are smaller and
contain partly **synthetic / future-dated** rows (models dated into 2026, an
`RTX 5090` entry, etc.) plus **deliberately injected quality defects**. This
specification uses the *real* figures from profiling `csv/` (Section 2) and treats
data cleansing as a first-class part of the ETL (Section 6.2).

---

## 2. Requirement analysis

### 2.1 Fact

A single fact: **GPU-model deployment compatibility**, the (many-to-many)
association between a GPU and an AI model, qualified by whether and how the model
can be served on that GPU.

### 2.2 Source datasets (as profiled from `csv/`)

| Dataset | File | Rows | Cols | Provenance / licence |
|---|---|---:|---:|---|
| Notable AI Models | `csv/notable_ai_models.csv` | **1,052** | 47 | Epoch AI, *Notable AI Models* (epoch.ai/data), CC-BY |
| Graphics-card full specs | `csv/gpu_specs_v7.csv` | **3,056** | 16 | Kaggle `alanjo/graphics-card-full-specs` (TechPowerUp-derived) |

The other model CSVs in the repo (`all_ai_models.csv` 24,019 rows;
`large_scale_ai_models.csv` 527; `frontier_ai_models.csv` 137) are
supersets/subsets of the same Epoch export and are **not used**, `notable_ai_models.csv`
is the canonical model dimension.

**Model source, column completeness (1,052 rows):**

| Column | Non-null | Null | Notes |
|---|---:|---:|---|
| `Model` | 1,052 | 0 | natural key |
| `Publication date` | 1,052 | 0 | 1950-07-02 → 2026-08-14 |
| `Domain` | 1,049 | 3 | multi-valued, comma-separated (`Multimodal,Language,Vision`) |
| `Organization` | 1,034 | 18 | free text, alias noise |
| `Parameters` | 720 | **332** | range 16 → 3×10¹² |
| `Training compute (FLOP)` | 536 | 516 | descriptive only |

Primary-domain distribution after normalisation (Section 5.5): Language 550,
Vision 205, Image generation 52, Games 49, Biology 43, Speech 38, Video 24,
Robotics 21, Other/misc 70. **Generative ≈ 672, non-generative ≈ 380.**
602 models were published in 2020 or later.

**GPU source, released ≥ 2016 (the modern deep-learning hardware era):
816 of 3,056 rows.** By manufacturer: NVIDIA 387, AMD 330, Intel 99.
Quality defects in this subset:

| Defect | Extent (≥ 2016 subset) |
|---|---|
| UTF-8 BOM on the header line | file-level |
| `memBusWidth` null | **628 / 816** (77 %), imputation is essential, not optional |
| `memClock` null | 78 / 816 |
| `memSize` (VRAM) null | 143 / 816 |
| `memType` dirty | 19 distinct spellings incl. leading-space dupes (`" GDDR6"`, `" GDDR6X"`, `" HBM2e"`, `" HBM3"`, `" GDDR7"`, `" LPDDR5"`, `" HBM3e"`), junk tokens (`VRAM`, `DRAM`, `SGR`, `CDRAM`), 78 null |
| `productName` duplicated | 84 rows (732 distinct of 816) |
| `releaseYear` | stored as float, 44 null (whole file) |
| Impossible cross-field combos | e.g. `GeForce RTX 5090` → `memType=HBM2e`, `gpuChip="Arctic Sound"` (Intel codename); `RTX 3050 6 GB` → `HBM3e`; perturbed magnitudes (`RTX 5090 memSize=28`) |

### 2.3 Preliminary workload

The three OLAP analyses from the proposal:

1. **Deployability over time**, how the share of state-of-the-art models that a
   given GPU generation can run has evolved, as both model size and hardware
   capacity scaled.
2. **VRAM-to-deployable-model trade-off**, which GPU generations (architectures)
   offer the best ratio of VRAM cost to number of modern LLMs deployable.
3. **Domain accessibility**, which AI domains (language, vision, multimodal, …)
   are most accessible **without** requiring quantization.

### 2.4 Granularity, volume, historical interval

- **Grain:** one row per `(GPU, model)` pair.
- **Volume:** ~816 GPUs × 1,052 models ≈ **0.86 M** fact rows (≈ 0.71 M if GPUs
  lacking a usable VRAM value are quarantined). Tractable for a single Postgres
  instance; the proposal's 1.75 M estimate assumed a larger model set.
- **Historical interval:** model publication 1950-2026; GPU release 2016-2025.
  Model publication date is the fact's **only genuine time axis**; GPU release
  year is a plain attribute of `DIM_GPU`.

### 2.5 Time-modelling decision: no separate `DIM_TIME`

The calendar hierarchy (`day → month → quarter → year → decade`) is **inlined on
`DIM_MODEL`** as ordinary attributes, not split into a standalone time dimension.
Rationale, weighed against the source data:

| Consideration | What the CSVs show | Implication |
|---|---|---|
| How many date FKs does the fact have? | Exactly one, the model's publication date. `gpu_specs_v7.csv` has no date column at all, only `releaseYear` (int). | No role-playing, no shared/conformed hierarchy → the classic reason for a dimension table (reuse across facts/FKs, per the "shared hierarchy" slide) does not apply. |
| Is the date real, or year-only noise? | `notable_ai_models.csv`: **1,052 / 1,052** rows carry a parseable date; **857 distinct dates**, 262 distinct months, all 31 days-of-month present, realistic weekday skew. Only **1.2 %** land on 1 Jan and **9.2 %** on a 1st-of-month. | Day/month precision is genuine and worth keeping, `release_month` / `release_quarter` stay. |
| Cardinality of a would-be `DIM_TIME` | ~857 rows (distinct dates) or ~28 k (contiguous 1950-2026 calendar). | Tiny, so the join is cheap, but it is still an **extra join on every time-sliced query** plus a calendar-build ETL step, bought for a single consumer. |
| Are non-derivable calendar attributes needed (fiscal periods, holidays, working-day flags)? | None appear in the workload (§2.3), every needed field is a pure function of the date. | Nothing a dimension table could add that four derived columns cannot. |
| Second fact planned? | No. Single fact, academically scoped, one-shot Refresh. | YAGNI, a conformed `DIM_TIME` would be dead weight. |

**Verdict:** drop `DIM_TIME`. Put `release_date, release_month, release_quarter,
release_year, release_decade` on `DIM_MODEL`; the fact needs **no** time key
(publication date is functionally determined by `model_key`: `model → date`).
Every "compatibility over time" query becomes `fact ⨝ dim_model` grouped by
`dim_model.release_year`, one join instead of two, with full roll-up/drill-down
preserved. This is the degenerate-hierarchy case from the lecture: a single-use
calendar hierarchy, fully derivable, cheaper to inline than to normalise out.

---

## 3. Conceptual design: Dimensional Fact Model

### 3.1 Fact schema (DFM)

```
   organization ──▶ orgCountry     paramBucket     primaryDomain ──▶ isGenerative
              ▲                          ▲                 ▲
              │                          │                 │
              └──────────────── [ MODEL ] ─────────────────┘
                                    │  │
   releaseDate ──▶ month ──▶ quarter ──▶ year ──▶ decade      calendar hierarchy,
     (model publication date; the hierarchy lives ON the        inlined on MODEL,
      MODEL dimension: no DIM_TIME table, no time FK)            fully derivable
                                    │
        ┌───────────────────────────┴────────────────┐
        │        FACT: GPU_MODEL_COMPATIBILITY        │
        │        identifier: { MODEL, GPU }           │
        │                                            │
        │  measures:                                 │
        │   • fits_in_vram        (boolean / COUNT)  │
        │   • vram_headroom_gb    (numeric, level)   │
        │   • model_vram_footprint_gb (numeric)      │
        │   • estimated_throughput (numeric*, unit)  │  * NULL for non-generative
        │   • throughput_unit     (varchar*)         │    degenerate, kept in fact
        │   • quantization_required (categorical)    │
        └─────────────────────┬──────────────────────┘
                              │
  releaseYear(gpu) ◀── [ GPU ] ──▶ memType ──▶ memFamily     (roll-up only)
                       │    │            │
          vramBucket ◀─┘    │            └╌╌▶ dataRate   (descriptive attr. of
                            │                             memType, see §3.2 note)
                            └──▶ gpuChip ──▶ gpuArchitecture ──▶ manufacturer
                              │
                     memoryBandwidthGbs (derived) · busWidthBit · memClockMhz · vramGb
```

### 3.2 Dimensions & hierarchies

| Dimension | Root | Hierarchies | Descriptive attributes |
|---|---|---|---|
| **MODEL** | model | `model → organization → orgCountry`; `model → primaryDomain (→ isGenerative)`; `model → paramBucket`; **`model → releaseDate → month → quarter → year → decade`** (calendar hierarchy inlined on this dimension, see §2.5) | `parameterCount*`, `trainingComputeFlop*`, `confidence*` |
| **GPU** | gpu | `gpu → gpuChip → gpuArchitecture → manufacturer`; `gpu → memType → memFamily`; `gpu → vramBucket` | `dataRate` (descriptive attr. of `memType`), `vramGb`, `memoryBandwidthGbs` (derived), `busWidthBit*`, `memClockMhz*`, `releaseYear*`, `bandwidthIsEstimated` |

> **`dataRate` is a descriptive attribute of `memType`, not a hierarchy level below
> `memFamily`.** `memType → memFamily` is a genuine roll-up (`GDDR6X → GDDR`,
> `HBM2e → HBM`), but `memFamily → dataRate` is **not** a functional dependency,
> the GDDR family alone spans several data rates (`GDDR5`≈4, `GDDR6`≈8,
> `GDDR6X`≈16). `dataRate` is fixed by the specific `memType` and is only a lookup
> constant feeding the `memoryBandwidthGbs` computation (§5.1); it adds no useful
> aggregation level, so it is a descriptive attribute (DFM sense), stored as a
> plain column on `dim_gpu`.

`*` = the attribute may be null (lecture convention).
There is **no `TIME` dimension**, the calendar hierarchy is materialised as
plain attributes of `MODEL` (§2.5). Time roll-up/drill-down is therefore done on
`DIM_MODEL` columns, with no join.

### 3.3 Measures & additivity

Along the **time** hierarchy = the `releaseDate → … → decade` chain on `MODEL`
(there is no separate `TIME` dimension).

| Measure | Type (Flow/Level/Unit) | time (on MODEL) | MODEL (other) | GPU | Notes |
|---|---|---|---|---|---|
| `fits_in_vram` | Flow (COUNT of pairs) | SUM/AVG/… | SUM/AVG/… | SUM/AVG/… | boolean; aggregates as "how many pairs fit" / "fit rate" |
| `vram_headroom_gb` | Level | AVG, MIN, MAX | AVG, MIN, MAX | **SUM**, AVG, MIN, MAX | additive only along GPU (summing headroom across models is meaningless) |
| `model_vram_footprint_gb` | Level | AVG, MIN, MAX | AVG, MIN, MAX | AVG, MIN, MAX | property of the model at fp16; non-additive everywhere |
| `estimated_throughput` | Unit | AVG, MIN, MAX | AVG, MIN, MAX | AVG, MIN, MAX | **NULL** for non-generative models; never SUM |
| `quantization_required` | categorical, not aggregated | n/a | n/a | n/a | used for slice/dice and COUNT |

`throughput_unit` is a **degenerate dimension** (single low-cardinality attribute:
`tokens/sec` \| `images/sec` \| NULL) stored directly in the fact table, per the
lecture's degenerate-dimension guidance, a dedicated table would add a join for
no analytical benefit.

**Empty-fact / COUNT semantics.** When `parameter_count` is unknown for a model,
`fits_in_vram`, `vram_headroom_gb` and `quantization_required` are NULL for every
pair involving that model; those pairs still exist in the fact table and are
counted, but excluded from `fits_in_vram` aggregates (`COUNT(*) FILTER (WHERE
fits_in_vram)` style).

### 3.4 Integrity constraints (stated separately, per DFM convention)

- **Identifier:** `{MODEL, GPU}` identifies a fact instance. The fact carries no
  time key, publication date is functionally determined by `MODEL`
  (`model → releaseDate`), so it is reached through `model_key`.
- **FDs in MODEL:** `model → organization`, `organization → orgCountry`,
  `model → primaryDomain`, `primaryDomain → isGenerative`, `model → paramBucket`,
  `model → releaseDate → month → quarter → year → decade` (calendar hierarchy,
  all steps derivable from `releaseDate`).
- **FDs in GPU:** `gpu → gpuChip → gpuArchitecture → manufacturer`,
  `gpu → memType → memFamily` (roll-up), `memType → dataRate` (lookup constant,
  **note `memFamily → dataRate` does *not* hold**: GDDR spans rates ~4-16),
  `gpu → vramBucket`.
- **Derived-measure rule:** `estimated_throughput IS NULL ⇔ throughput_unit IS
  NULL ⇔ NOT isGenerative` (or `parameter_count` unknown).
- `quantization_required = 'does-not-fit' ⇔ fits_in_vram = false` at every
  quantization tier.

---

## 4. Logical design: ROLAP star schema

### 4.1 Star vs snowflake

**Star schema** with **two dimensions** (`dim_model`, `dim_gpu`) and **no
`dim_time`** (§2.5). The dimension tables are tiny (`dim_model` ≤ 1,052 rows,
`dim_gpu` ≤ 816); the redundancy cost of denormalising the hierarchies is
negligible, while a star removes all dimension-to-dimension joins from OLAP
queries. Snowflaking would only pay off if a secondary dimension table's
cardinality vastly exceeded the primary's (lecture "Star vs Snowflake"), not the
case here. `memType → memFamily`, `memType → dataRate`, `gpuChip →
gpuArchitecture` and the `releaseDate → … → decade` calendar chain are all kept
as denormalised columns (inside `dim_gpu` and `dim_model` respectively).

### 4.2 DDL (target for `database/schema.sql`)

```sql
-- ============================================================================
--  WeightBox ROLAP star schema
--  (the ODS layer, ODS_MODELS / ODS_GPUS + reject/audit tables, is defined
--   in Section 6.1; it lives in schema `ods`)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS ods;

-- ----------------------------------------------------------------------------
--  DIM_MODEL   (the calendar hierarchy is inlined here, there is no DIM_TIME,
--               see Section 2.5)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_model (
    model_key             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_nk              text        NOT NULL UNIQUE,       -- Model name (natural key)
    model_name            text        NOT NULL,
    organization          text        NOT NULL DEFAULT 'Unknown',
    organization_country  text        NOT NULL DEFAULT 'Unknown',
    primary_domain        text        NOT NULL,              -- normalised single domain
    is_generative         boolean     NOT NULL,
    parameter_count       numeric,                           -- * nullable (332 models)
    parameter_bucket      text        NOT NULL,              -- '<1B','1-7B','7-13B',...,'unknown'
    throughput_unit       text,                              -- descriptive attr of primary_domain (Appendix C)
    training_compute_flop numeric,                           -- * nullable, descriptive
    -- calendar hierarchy, all derived from release_date (day -> month -> quarter -> year -> decade)
    release_date          date        NOT NULL,              -- Epoch 'Publication date' (1052/1052 valid)
    release_month         smallint    NOT NULL,              -- 1..12
    release_quarter       smallint    NOT NULL,              -- 1..4
    release_year          smallint    NOT NULL,
    release_decade        smallint    NOT NULL,              -- e.g. 2020
    confidence            text,                              -- * Epoch 'Confidence' field
    source_dataset        text        NOT NULL DEFAULT 'notable_ai_models'
);

-- ----------------------------------------------------------------------------
--  DIM_GPU
-- ----------------------------------------------------------------------------
CREATE TABLE dim_gpu (
    gpu_key               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gpu_nk                text        NOT NULL UNIQUE,       -- productName + '|' + releaseYear
    product_name          text        NOT NULL,
    manufacturer          text        NOT NULL,
    gpu_chip              text,                              -- * nullable / suspect
    gpu_architecture      text        NOT NULL DEFAULT 'Unknown',
    release_year          smallint,                          -- * 44 null in source
    vram_gb               numeric     NOT NULL,
    vram_bucket           text        NOT NULL,              -- '<=4','8','12','16','24','32-48','>48'
    mem_bus_width_bit     integer,                           -- * 77% null -> imputed
    mem_clock_mhz         numeric,                           -- *
    mem_type              text        NOT NULL,              -- canonical: GDDR5/6/6X/7, HBM2/2e/3/3e, DDR...
    mem_family            text        NOT NULL,              -- roll-up of mem_type: GDDR / HBM / DDR / LPDDR
    data_rate             numeric     NOT NULL,              -- lookup keyed on mem_type (NOT mem_family); Appendix B.1
    memory_bandwidth_gbs  numeric     NOT NULL,              -- derived (Section 5.1)
    bandwidth_is_estimated boolean    NOT NULL DEFAULT false,
    specs_suspect         boolean     NOT NULL DEFAULT false -- failed a cross-field consistency check
);

-- ----------------------------------------------------------------------------
--  FACT_GPU_MODEL_COMPATIBILITY  (grain: one (gpu, model) pair)
-- ----------------------------------------------------------------------------
CREATE TABLE fact_gpu_model_compatibility (
    gpu_key                  bigint  NOT NULL REFERENCES dim_gpu(gpu_key),
    model_key                bigint  NOT NULL REFERENCES dim_model(model_key),
    -- no time key: model publication date is reached via model_key (model -> release_date)
    model_nk                 text    NOT NULL,   -- denormalised dim_model.model_nk; carries ix_fact_model_nk
    gpu_nk                   text    NOT NULL,   -- denormalised dim_gpu.gpu_nk; carries ix_fact_gpu_nk

    model_vram_footprint_gb  numeric,            -- fp16 footprint incl. overhead; NULL if params unknown
    fits_in_vram             boolean,            -- NULL if params unknown
    vram_headroom_gb         numeric,            -- vram_gb - footprint_fp16 ; NULL if params unknown
    quantization_required    text,               -- 'none'|'8-bit'|'4-bit'|'does-not-fit'|NULL
    estimated_throughput     numeric,            -- * NULL for non-generative / params unknown / no bandwidth
    throughput_unit          varchar(12),        -- 'tokens/sec'|'images/sec'|NULL  (degenerate dim)

    PRIMARY KEY (gpu_key, model_key)
);
```

`model_nk` and `gpu_nk` are denormalised copies of the two dimension natural
keys. They are functionally determined by `model_key` and `gpu_key`, so they add
no information, but they let a name filter ("which GPUs run Llama-3") scan the
fact table without joining a dimension. Each carries one of the two required
fact indexes (§8).

### 4.3 Junk-dimension alternative (documented, not adopted)

`throughput_unit` (3 values incl. NULL) × `quantization_required` (5 values) yields
≤ 15 combinations, a textbook **junk dimension** `dim_deployment_flags`. It is
*not* adopted: both attributes are kept in the fact table (degenerate) because the
combination count is tiny and inlining them avoids a join on every OLAP query.
The junk-dimension option is recorded here so the trade-off is on the record.

---

## 5. Derived-attribute computation

All formulas below are computed once, during ETL (Refresh load).

### 5.1 GPU memory bandwidth

```
memory_bandwidth_gbs = mem_clock_mhz × mem_bus_width_bit × data_rate / 8000
```

Units: `mem_clock_mhz` in MHz (TechPowerUp reports the **real** memory clock, not
the effective/marketing clock), `mem_bus_width_bit` in bits; `/8` converts bits→
bytes and `/1000` MHz→GHz, hence `/8000`. `data_rate` (transfers per clock) is
looked up **by `mem_type`** (not `mem_family`, see Appendix B.1 and §3.2).

**Missing `mem_bus_width_bit`.** Present in the source for ~188 of the 816
`≥ 2016` rows (all 2022 or later); for those the source value is used as-is and
`bandwidth_is_estimated` stays `false`. For the rest, impute in this order:

1. Curated `product_name` → bus-width map (Appendix B.2, 17 pre-2022 cards).
   Set `bandwidth_is_estimated = true`.
2. Else, the modal bus width for that `mem_type` among rows that *do* have it
   (e.g. desktop GDDR6 → 256); this covers ~536 rows. Set
   `bandwidth_is_estimated = true`.
3. Else, if `mem_clock_mhz` is also missing → **quarantine** the GPU to
   `ods.reject_gpus` (reason `insufficient_memory_specs`).

### 5.2 Model VRAM footprint

```
model_vram_footprint_gb(bpw) = parameter_count × bpw × OVERHEAD / 1e9
```

- `bpw` (bytes per weight): fp16 = 2, int8 = 1, int4 = 0.5.
- `OVERHEAD = 1.20`, a flat allowance for activations, KV cache and runtime
  (documented assumption, Appendix D; not a claim of exactness).
- If `parameter_count IS NULL` → footprint, `fits_in_vram`, `vram_headroom_gb`,
  `quantization_required` are all NULL for that model's pairs.

### 5.3 Fit & headroom

```
fits_in_vram      = (model_vram_footprint_gb(fp16) <= vram_gb)
vram_headroom_gb  = vram_gb - model_vram_footprint_gb(fp16)      -- may be negative
```

### 5.4 Quantization ladder

First tier whose footprint fits; else `does-not-fit`:

| Tier | Condition |
|---|---|
| `none` | `footprint(fp16) ≤ vram_gb` |
| `8-bit` | `footprint(int8) ≤ vram_gb` |
| `4-bit` | `footprint(int4) ≤ vram_gb` |
| `does-not-fit` | otherwise |

### 5.5 Primary domain & `is_generative`

`Domain` is a comma-separated multi-value string. Reduce to one `primary_domain`
by first match in this priority order:

```
Language, Multimodal, Image generation, Video, Speech, Audio,
Vision, Games, Biology, Robotics, Recommendation, Mathematics, Other
```

`is_generative = primary_domain ∈ {Language, Multimodal, Image generation, Video,
Speech, Audio}` (full mapping in Appendix C). When `Domain` is null, fall back to
`Task` keywords (`generation`, `chat`, `language modeling` → Language; `image` →
Image generation; …); if still unresolved → `primary_domain = 'Other'`,
`is_generative = false`.

### 5.6 Estimated throughput (generative models only)

```
estimated_throughput = memory_bandwidth_gbs / (model_vram_footprint_gb(fp16))
```

i.e. the memory-bandwidth-bound ceiling `bandwidth / bytes_touched_per_token`
(active bytes per token ≈ the fp16 weight footprint for a dense model). Real
engines reach ≈ 50-75 % of this; the derate is **not** stored, it is documented
in Appendix D and applied by the Next.js frontend at display time if desired.

| `primary_domain` | `throughput_unit` |
|---|---|
| Language, Multimodal, Speech, Audio, Video | `tokens/sec` |
| Image generation | `images/sec` (interpret the ratio as images/s) |
| anything non-generative, or `parameter_count` NULL, or `memory_bandwidth_gbs` NULL | `estimated_throughput = NULL`, `throughput_unit = NULL` |

### 5.7 Buckets

- `parameter_bucket`: `<1B`, `1-7B`, `7-13B`, `13-34B`, `34-70B`, `70-180B`,
  `>180B`, `unknown`.
- `vram_bucket`: `<=4`, `6-8`, `10-12`, `16`, `24`, `32-48`, `>48` (GB).

---

## 6. ETL pipeline

Python 3.12 + pandas + SQLAlchemy + psycopg, packaged as the one-shot `etl`
service (`docker compose --profile etl run --rm etl`). Load strategy: **Refresh**
(static extraction, full rebuild), appropriate for the first and only population
of a read-only warehouse. The ETL is a **single one-time script** run in two
passes:

- **Pass 1, raw load to the ODS.** Each CSV is copied *verbatim* into an ODS
  table (`ODS_MODELS`, `ODS_GPUS`); no filtering, no type coercion.
- **Pass 2, ODS → star schema.** Every subsequent phase (cleansing,
  transformation, loading) reads **only** from the ODS tables, the CSV files are
  never touched again. This isolates "get the data in" from "make it correct",
  per the lecture's reconciliation model.

Pipeline stages mirror the lecture's four ETL phases (Pass 1 = Extraction;
Pass 2 = Cleansing + Transformation + Loading).

### 6.1 Extraction, raw load to the ODS

Read `csv/notable_ai_models.csv` and `csv/gpu_specs_v7.csv` verbatim: one ODS row
per CSV **record** (a proper CSV parser is required, `Abstract` and notes fields
carry embedded newlines so `wc -l` overcounts), every column typed `text`,
headers slugified, no filtering. `encoding='utf-8-sig'` strips the BOM on the GPU
file. This is the only step that reads the filesystem; every later phase reads
the ODS tables.

`ods.ods_gpus` mirrors the 16 GPU columns:
`manufacturer, product_name, release_year, mem_size, mem_bus_width, gpu_clock,
mem_clock, unified_shader, tmu, rop, pixel_shader, vertex_shader, igp, bus,
mem_type, gpu_chip`.

`ods.ods_models` mirrors the 47 model columns:
`model, organization, publication_date, domain, task, parameters,
parameters_notes, training_compute_flop, training_compute_notes,
training_dataset, training_dataset_size_total, dataset_size_notes, confidence,
link, reference, citations, authors, abstract, organization_categorization,
country_of_organization, notability_criteria, notability_criteria_notes, epochs,
training_time_hours, training_time_notes, training_hardware, hardware_quantity,
hardware_utilization_mfu, training_compute_cost_2023_usd, compute_cost_notes,
training_power_draw_w, base_model, finetune_compute_flop, finetune_compute_notes,
batch_size, batch_size_notes, model_accessibility, training_code_accessibility,
inference_code_accessibility, accessibility_notes, numerical_format,
frontier_model, hardware_acquisition_cost, hardware_utilization_hfu,
training_compute_cost_cloud, training_compute_cost_upfront, open_model_weights`.

Both tables also carry `ods_*_id` (identity), `_source_sha256` and `_loaded_at`.

```sql
CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE ods.ods_gpus (
    ods_gpu_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    manufacturer text, product_name text, release_year text, mem_size text,
    mem_bus_width text, gpu_clock text, mem_clock text, unified_shader text,
    tmu text, rop text, pixel_shader text, vertex_shader text,
    igp text, bus text, mem_type text, gpu_chip text,
    _source_sha256 text NOT NULL,
    _loaded_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ods.ods_models (
    ods_model_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model text, organization text, publication_date text, /* ... 44 more ... */
    open_model_weights text,
    _source_sha256 text NOT NULL,
    _loaded_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ods.load_audit (
    load_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ods_table text NOT NULL, file_name text NOT NULL, sha256 text NOT NULL,
    row_count integer NOT NULL, loaded_at timestamptz NOT NULL DEFAULT now()
);
```

The loader computes the file sha256. If `ods.load_audit` already has a row with
that sha256 and the ODS table is non-empty, the upload is skipped
(`ETL_SKIP_ODS_IF_LOADED`). Otherwise the ODS table is truncated, reloaded via
`COPY`, and one `load_audit` row plus one `ods.profile_log` row per column
(empty rate) are written. `ods.reject_models` / `ods.reject_gpus` hold
`(natural_key, rule, detail)` for rows dropped in cleansing.

### 6.2 Cleansing (value correction)

Reads from `ODS_MODELS` / `ODS_GPUS`. Every rule counts its hits (logged at the
end of Phase 2) and routes rejected rows to `ods.reject_gpus` /
`ods.reject_models` (`(natural_key, rule, detail)`).

**GPU rules**

| # | Rule |
|---|---|
| G1 | `releaseYear`: `float → int`; drop rows `< 2016` (reason `pre_2016`); null year kept but flagged. |
| G2 | `memType`: `strip()`, collapse internal whitespace, upper-case; map to canonical `mem_type` via Appendix B.1, then derive `mem_family` (roll-up) and `data_rate` (lookup) **from that `mem_type`**. Junk tokens (`VRAM`, `DRAM`, `SGR`, `CDRAM`, `SDR`, `EDO`, `FPM`, …) and null → try to infer `mem_type` from another row with the same `gpu_chip`; else reject (`unknown_memory_type`). |
| G3 | `memSize` (VRAM): to numeric GB; `0`/null → reject (`missing_vram`) unless recoverable from the Appendix B.2 curated map. |
| G4 | `mem_bus_width_bit`: impute per Section 5.1 (curated map → modal-by-type → reject). |
| G5 | `mem_clock_mhz`: to numeric; null → modal by `mem_type`+`release_year`; still null → reject (`missing_mem_clock`). |
| G6 | De-duplicate `product_name` (84 dupes): group by `product_name`, keep the row with the most non-null spec columns; tie-break on latest `releaseYear`. Natural key becomes `product_name + '|' + release_year`. |
| G7 | Cross-field consistency: check `(gpu_chip, mem_type, manufacturer)` plausibility against a rule table (e.g. GeForce/Radeon consumer card ⇏ HBM; NVIDIA chip codename ⇏ Intel `Arctic Sound`). On violation: correct from the curated map if the product is known, else keep the row but set `specs_suspect = true` and `bandwidth_is_estimated = true`. Count reported, not rejected, the analyses tolerate approximate bandwidth. |
| G8 | Derive `gpu_architecture` from `gpu_chip` / `product_name` via a lookup table (Ada, Ampere, Hopper, Blackwell, RDNA2/3/4, Arc Alchemist/Battlemage, …); unresolved → `'Unknown'`. |

**Model rules**

| # | Rule |
|---|---|
| M1 | `Model`: `strip()`; must be unique (natural key), on collision keep the row with the most non-null columns, reject the other (`duplicate_model`). |
| M2 | `Publication date` → `date` → `release_date`; unparseable → reject (`bad_publication_date`), in the current CSV **all 1,052 rows parse**. Derive `release_month`, `release_quarter`, `release_year`, `release_decade` from it (no separate time table). |
| M3 | `Parameters` → numeric; **null is allowed** (332 rows). Such models stay in `dim_model` with `parameter_bucket='unknown'`; their fact rows carry NULL fit/quant/throughput measures. Implausible values (`< 1e3` or `> 5e12`) → null + count. |
| M4 | `Domain`: null → infer from `Task` (Section 5.5); derive `primary_domain`, `is_generative`. |
| M5 | `Organization`: `strip()`; apply alias table (`Google DeepMind`/`DeepMind`/`Google` families, `Meta AI`/`Facebook AI Research`, `Z.ai`/`Zhipu AI`, …); null → `'Unknown'`. `organization_country`: from `Country (of organization)` directly (first comma-segment, UN-style long names shortened, e.g. `United States of America` → `United States`); blank → `'Unknown'`. No per-organisation country guessing: the source column is populated for every model that has a country, and a lookup keyed on organisation disagreed with it on ~330 of 1,052 rows. |
| M6 | `Confidence` passed through as-is (descriptive). |

### 6.3 Transformation (format & structure)

- Assign surrogate keys (`IDENTITY`); denormalise each hierarchy into its
  dimension row (organization+country and the `release_*` calendar columns in
  `dim_model`; `gpu_chip`+`gpu_architecture`+`manufacturer`, `mem_type`+
  `mem_family` in `dim_gpu`).
- Compute `release_month/quarter/year/decade` from `release_date`;
  `parameter_bucket`, `vram_bucket`; look up `data_rate` from `mem_type`
  (Appendix B.1) then compute `memory_bandwidth_gbs` (§5.1).
- Unit/format conventions: VRAM and footprints in GB (numeric), bandwidth in
  GB/s, `release_date` as SQL `date`.

### 6.4 Loading (Refresh)

1. `TRUNCATE fact_gpu_model_compatibility, dim_gpu, dim_model RESTART IDENTITY
   CASCADE`.
2. Bulk-load `dim_gpu`, `dim_model` via `COPY`; identities auto-assign.
3. Seed `validator_fact_nulls` (§6.5): one row per nullable fact attribute with
   `null_allowed = true`, its NULL rule, `status = 'pending'`.
4. Build the fact set-based. `throughput_unit` is precomputed onto `dim_model`
   during transformation (it is a function of `primary_domain`), so the INSERT
   reads `m.throughput_unit` directly:

   ```sql
   INSERT INTO fact_gpu_model_compatibility
       (gpu_key, model_key, model_nk, gpu_nk,
        model_vram_footprint_gb, fits_in_vram, vram_headroom_gb,
        quantization_required, estimated_throughput, throughput_unit)
   SELECT
       g.gpu_key, m.model_key, m.model_nk, g.gpu_nk,
       fp.footprint_fp16,
       (fp.footprint_fp16 <= g.vram_gb)                          AS fits_in_vram,
       (g.vram_gb - fp.footprint_fp16)                           AS vram_headroom_gb,
       CASE
         WHEN m.parameter_count IS NULL      THEN NULL
         WHEN fp.footprint_fp16 <= g.vram_gb THEN 'none'
         WHEN fp.footprint_int8 <= g.vram_gb THEN '8-bit'
         WHEN fp.footprint_int4 <= g.vram_gb THEN '4-bit'
         ELSE 'does-not-fit'
       END                                                       AS quantization_required,
       CASE WHEN m.is_generative AND m.parameter_count IS NOT NULL
                 AND g.memory_bandwidth_gbs IS NOT NULL
            THEN g.memory_bandwidth_gbs / NULLIF(fp.footprint_fp16, 0) END AS estimated_throughput,
       CASE WHEN m.is_generative AND m.parameter_count IS NOT NULL
                 AND g.memory_bandwidth_gbs IS NOT NULL
            THEN m.throughput_unit END                           AS throughput_unit
   FROM dim_gpu g
   CROSS JOIN dim_model m
   LEFT JOIN LATERAL (
       SELECT
         m.parameter_count * 2   * :overhead / 1e9 AS footprint_fp16,
         m.parameter_count * 1   * :overhead / 1e9 AS footprint_int8,
         m.parameter_count * 0.5 * :overhead / 1e9 AS footprint_int4
   ) fp ON true;
   ```

5. Check `validator_fact_nulls` (§6.5): fill the actual counts, grade each row
   `pass` or `fail` against its rule, and abort when `ETL_FAIL_FAST` and any
   row failed.
6. Post-load assertions, abort on violation:
   `COUNT(fact) = COUNT(dim_gpu) * COUNT(dim_model)`; no orphan FKs;
   `quantization_required = 'does-not-fit'` implies `fits_in_vram = false`;
   `model_nk` and `gpu_nk` populated on every row.
7. `REFRESH MATERIALIZED VIEW` for every `mv_*` (Section 7); `ANALYZE`.
8. Log the run summary as plain lines (no file): per-rule counts, reject-table
   sizes, final dimension and fact row counts, validator status.

### 6.5 Schema and data-health validation

Two checks, both in code, backed by one persistent table.

**Schema check (Phase 1).** Every table is defined once as a `TableSpec` object
that both renders its `CREATE TABLE` and is compared against the live database:
missing table, missing column, wrong base type, or wrong nullability aborts
before any data is written.

**Fact NULL audit.** `validator_fact_nulls` has one row per nullable fact
attribute:

```sql
CREATE TABLE validator_fact_nulls (
    attribute      text PRIMARY KEY,
    null_allowed   boolean NOT NULL,
    null_rule      text NOT NULL,
    null_count     bigint,
    not_null_count bigint,
    total_rows     bigint,
    status         text NOT NULL DEFAULT 'pending',   -- 'pending' | 'pass' | 'fail'
    detail         text,
    checked_at     timestamptz
);
```

It is **initialised** just before the fact INSERT (six `pending` rows) and
**checked** just after: each row gets its `null_count` / `not_null_count` /
`total_rows`, then a per-attribute query counts the rows that break the rule
(zero means `pass`). The rules:

| attribute | rule (violation count must be 0) |
|---|---|
| `model_vram_footprint_gb` | `NULL` iff `dim_model.parameter_count` is `NULL` |
| `fits_in_vram` | `NULL` iff `model_vram_footprint_gb` is `NULL` |
| `vram_headroom_gb` | `NULL` iff `model_vram_footprint_gb` is `NULL` |
| `quantization_required` | `NULL` iff `model_vram_footprint_gb` is `NULL` |
| `estimated_throughput` | `NULL` unless `is_generative` and `parameter_count` and bandwidth all present |
| `throughput_unit` | `NULL` iff `estimated_throughput` is `NULL` |

---

## 7. OLAP layer: queries & materialized views

For each proposal analysis: the natural-language query, its DFM aggregation
pattern (group-by set), and SQL over the star schema.

### 7.1 Deployability of SOTA models over time

*Group-by set:* `{ model.release_year, gpu.gpu_architecture }`
*Measures:* fit rate, avg headroom.

```sql
SELECT  m.release_year,
        g.gpu_architecture,
        COUNT(*)                                          AS pairs,
        COUNT(*) FILTER (WHERE f.fits_in_vram)            AS pairs_fit,
        ROUND(AVG((f.fits_in_vram)::int)::numeric, 3)     AS fit_rate,
        ROUND(AVG(f.vram_headroom_gb)::numeric, 1)        AS avg_headroom_gb
FROM    fact_gpu_model_compatibility f
JOIN    dim_model m ON m.model_key = f.model_key
JOIN    dim_gpu   g ON g.gpu_key   = f.gpu_key
WHERE   f.fits_in_vram IS NOT NULL
GROUP BY m.release_year, g.gpu_architecture
ORDER BY m.release_year, g.gpu_architecture;
```

### 7.2 VRAM-to-deployable-model trade-off for modern LLMs

*Group-by set:* `{ gpu.gpu_architecture, gpu.vram_bucket }`, sliced to
`primary_domain='Language'` and `release_year >= 2020`.

```sql
SELECT  g.gpu_architecture,
        g.vram_bucket,
        ROUND(AVG(g.vram_gb)::numeric,0)                          AS avg_vram_gb,
        COUNT(DISTINCT f.model_key) FILTER
              (WHERE f.quantization_required = 'none')            AS llms_no_quant,
        COUNT(DISTINCT f.model_key) FILTER
              (WHERE f.fits_in_vram)                              AS llms_fp16_fit,
        ROUND( COUNT(DISTINCT f.model_key)
               FILTER (WHERE f.fits_in_vram)
             / NULLIF(AVG(g.vram_gb),0), 2)                       AS llms_per_gb
FROM    fact_gpu_model_compatibility f
JOIN    dim_gpu   g ON g.gpu_key   = f.gpu_key
JOIN    dim_model m ON m.model_key = f.model_key
WHERE   m.primary_domain = 'Language' AND m.release_year >= 2020
GROUP BY g.gpu_architecture, g.vram_bucket
ORDER BY llms_per_gb DESC;
```

### 7.3 Domain accessibility without quantization

*Group-by set:* `{ model.primary_domain, gpu.vram_bucket }`.

```sql
SELECT  m.primary_domain,
        g.vram_bucket,
        COUNT(DISTINCT f.model_key)                                       AS models_total,
        COUNT(DISTINCT f.model_key) FILTER
              (WHERE f.quantization_required = 'none')                    AS models_no_quant,
        ROUND( 100.0 * COUNT(DISTINCT f.model_key)
               FILTER (WHERE f.quantization_required = 'none')
             / NULLIF(COUNT(DISTINCT f.model_key),0), 1)                  AS pct_no_quant
FROM    fact_gpu_model_compatibility f
JOIN    dim_model m ON m.model_key = f.model_key
JOIN    dim_gpu   g ON g.gpu_key   = f.gpu_key
WHERE   f.quantization_required IS NOT NULL
GROUP BY m.primary_domain, g.vram_bucket
ORDER BY m.primary_domain, g.vram_bucket;
```

### 7.4 Materialized views

| View | Group-by set | Stored measures (incl. support measures) |
|---|---|---|
| `mv_deployability_by_year_arch` | `{model.release_year, gpu.gpu_architecture}` | `pairs`, `pairs_fit`, `sum_headroom_gb`, `n_headroom` (→ AVG reconstructable) |
| `mv_gpu_generation_tradeoff` | `{gpu.gpu_architecture, model.parameter_bucket}` | `models_deployable`, `sum_throughput`, `n_throughput`, `min_throughput`, `max_throughput` |
| `mv_domain_accessibility` | `{model.primary_domain, gpu.vram_bucket}` | `models_total`, `models_no_quant`, `models_8bit`, `models_4bit` |

**Support/derived measures.** Per the lecture ("Secondary views and aggregation"),
each view stores **COUNT and SUM** rather than AVG so that further roll-up (e.g.
architecture-only) recomputes correct averages; `AVG` and `%` are derived at query
time. `MIN`/`MAX` are distributive and stored directly.

```sql
CREATE MATERIALIZED VIEW mv_deployability_by_year_arch AS
SELECT m.release_year,
       g.gpu_architecture,
       COUNT(*)                                   AS pairs,
       COUNT(*) FILTER (WHERE f.fits_in_vram)     AS pairs_fit,
       SUM(f.vram_headroom_gb)                    AS sum_headroom_gb,
       COUNT(f.vram_headroom_gb)                  AS n_headroom
FROM   fact_gpu_model_compatibility f
JOIN   dim_model m ON m.model_key = f.model_key
JOIN   dim_gpu   g ON g.gpu_key   = f.gpu_key
GROUP BY m.release_year, g.gpu_architecture;
-- (mv_gpu_generation_tradeoff and mv_domain_accessibility analogously)
```

The ETL loader runs `REFRESH MATERIALIZED VIEW` for all three after the fact load.

---

## 8. Physical optimization

- **Required fact indexes:** `ix_fact_model_nk` on `fact(model_nk)` and
  `ix_fact_gpu_nk` on `fact(gpu_nk)`, created in Phase 3, which fails if either
  is absent afterwards. They serve name-filtered scans of the fact table.
- **Supporting indexes:** `fact(gpu_key)`, `fact(model_key)`, partial
  `fact(model_key) WHERE fits_in_vram` for the fit-rate queries,
  `dim_model(primary_domain)`, `dim_model(release_year)`,
  `dim_gpu(gpu_architecture)`, `dim_gpu(vram_bucket)`.
- **Denormalisation:** star schema keeps every OLAP query to `fact ⨝ dim`
  (**at most 2 joins**, `dim_model` + `dim_gpu`; folding the calendar hierarchy
  onto `dim_model` removed the third).
- **Materialized views** (Section 7.4) pre-aggregate the three canonical
  analyses; `ANALYZE` after load so the planner has fresh statistics.
- **Future work:** an *aggregate navigator* that rewrites incoming OLAP queries
  onto the coarsest sufficient `mv_*`, noted, not implemented (commercial
  navigators handle only distributive operators, which is why the views store
  SUM/COUNT).

---

## 9. Appendices

### Appendix A: Column dictionary (source → warehouse)

**`dim_model`**

| Column | Type | Source column | Transform | Nullable |
|---|---|---|---|---|
| `model_nk` / `model_name` | text | `Model` | strip, dedupe (M1) | no |
| `organization` | text | `Organization` | strip, alias table (M5) | no (`'Unknown'`) |
| `organization_country` | text | `Country (of organization)` | first comma-segment, long-name shortening (M5) | no (`'Unknown'`) |
| `primary_domain` | text | `Domain` (+ `Task`) | multi-value → priority pick (5.5) | no |
| `is_generative` | boolean | derived | Appendix C | no |
| `throughput_unit` | text | derived | Appendix C (function of `primary_domain`) | yes |
| `parameter_count` | numeric | `Parameters` | to numeric, plausibility (M3) | **yes** |
| `parameter_bucket` | text | derived | binning (5.7) | no |
| `training_compute_flop` | numeric | `Training compute (FLOP)` | to numeric | yes |
| `release_date` | date | `Publication date` | parse (M2) | no |
| `release_month` / `release_quarter` / `release_year` / `release_decade` | smallint | `Publication date` | derived from `release_date` (M2), calendar hierarchy inlined, no `DIM_TIME` | no |
| `confidence` | text | `Confidence` | pass-through | yes |

**`dim_gpu`**

| Column | Type | Source column | Transform | Nullable |
|---|---|---|---|---|
| `gpu_nk` | text | `productName`+`releaseYear` | concat (G6) | no |
| `product_name` | text | `productName` | strip | no |
| `manufacturer` | text | `manufacturer` | strip | no |
| `gpu_chip` | text | `gpuChip` | strip; suspect-flag (G7) | yes |
| `gpu_architecture` | text | `gpuChip`/`productName` | lookup (G8) | no (`'Unknown'`) |
| `release_year` | smallint | `releaseYear` | float→int, ≥2016 (G1) | yes |
| `vram_gb` | numeric | `memSize` | to GB, ≠0 (G3) | no |
| `vram_bucket` | text | derived | binning (5.7) | no |
| `mem_bus_width_bit` | int | `memBusWidth` | impute (G4 / 5.1) | yes |
| `mem_clock_mhz` | numeric | `memClock` | to numeric, impute (G5) | yes |
| `mem_type` | text | `memType` | normalise (G2, App. B.1) | no |
| `mem_family` | text | derived from `mem_type` (roll-up) | App. B.1 | no |
| `data_rate` | numeric | derived from `mem_type` (lookup constant, **not** from `mem_family`) | App. B.1 | no |
| `memory_bandwidth_gbs` | numeric | derived | formula (5.1) | no |
| `bandwidth_is_estimated` | boolean | derived | set on imputation (G4/G7) | no |
| `specs_suspect` | boolean | derived | cross-field check (G7) | no |

**`fact_gpu_model_compatibility`**

| Column | Type | Source | Nullable |
|---|---|---|---|
| `gpu_key` | bigint | FK `dim_gpu(gpu_key)` | no |
| `model_key` | bigint | FK `dim_model(model_key)` | no |
| `model_nk` | text | denormalised `dim_model.model_nk` | no |
| `gpu_nk` | text | denormalised `dim_gpu.gpu_nk` | no |
| `model_vram_footprint_gb` | numeric | fp16 footprint incl. overhead (§5.2) | yes |
| `fits_in_vram` | boolean | §5.3 | yes |
| `vram_headroom_gb` | numeric | §5.3 | yes |
| `quantization_required` | text | ladder §5.4 (`none`/`8-bit`/`4-bit`/`does-not-fit`) | yes |
| `estimated_throughput` | numeric | §5.6 | yes |
| `throughput_unit` | varchar | `dim_model.throughput_unit` when generative | yes |

Primary key `(gpu_key, model_key)`. The five measure columns are NULL together
when `parameter_count` is unknown; `estimated_throughput` and `throughput_unit`
are additionally NULL for non-generative models. `validator_fact_nulls`
(§6.5) enforces this.

### Appendix B: Memory technology reference

**B.1 `memType` → canonical type, family (roll-up), data rate (lookup)**

`data_rate` is keyed on the canonical **`mem_type`**, *not* on `mem_family`, the
GDDR family alone spans rates 4-16, so `mem_family` cannot determine it. Read this
as a small ETL cross-reference table.

| Raw (after trim+upper) | `mem_type` | `mem_family` | `data_rate` |
|---|---|---|---|
| `DDR`, `SDR`, `EDO`, `FPM` | `DDR` | `DDR` | 2 |
| `DDR2` | `DDR2` | `DDR` | 2 |
| `DDR3`, `GDDR3` | `GDDR3` | `GDDR` | 2 |
| `GDDR4` | `GDDR4` | `GDDR` | 2 |
| `GDDR5` | `GDDR5` | `GDDR` | **4** |
| `GDDR5X` | `GDDR5X` | `GDDR` | **8** |
| `GDDR6` | `GDDR6` | `GDDR` | **8** |
| `GDDR6X` | `GDDR6X` | `GDDR` | **16** (PAM4) |
| `GDDR7` | `GDDR7` | `GDDR` | **16** (PAM3; ~24 eff., calibrate) |
| `HBM` | `HBM` | `HBM` | 2 |
| `HBM2`, `HBM2E` | `HBM2e` | `HBM` | 2 |
| `HBM3`, `HBM3E` | `HBM3` | `HBM` | 2 |
| `LPDDR4X`, `LPDDR5` | `LPDDR5` | `LPDDR` | 4 |
| `VRAM`, `DRAM`, `SGR`, `SGRAM`, `CDRAM`, `EDRAM`, `` (null) | n/a | n/a | infer from a same-chip sibling, else reject (G2) |

> Within one `mem_family` (`GDDR`) the rate ranges from 4 (`GDDR5`) to 16
> (`GDDR6X`), proof that `mem_family → data_rate` is not a functional dependency.
> The values above assume TechPowerUp's **real** (not effective) memory clock;
> the ETL must verify them against a handful of known cards (e.g. RTX 3070 →
> 448 GB/s, RTX 4090 → 1008 GB/s, A100 40 GB → 1555 GB/s) because `gpu_specs_v7.csv`
> is partly perturbed. Sources: `docs/lessons/DataWarehousing.pdf`;
> <https://en.wikipedia.org/wiki/GDDR6_SDRAM>;
> <https://www.atlantic.net/gpu-server-hosting/gpu-memory-bandwidth/>.

**B.2 Curated bus-width / VRAM map (for imputation G3/G4).**
A hand-maintained table keyed by canonical `product_name`, **17 entries**, only
the cards whose `memBusWidth` the source CSV omits: RTX 3060/3070/3080/3090,
RTX 4060 Ti, RTX 2080 Ti, GTX 1060/1080/1080 Ti, RX 6700 XT/6800/6800 XT/6900 XT,
A100 (PCIe and SXM4, 40 GB and 80 GB). Newer parts (RTX 40/50 series, RX 7900,
Arc A7xx, H100, L4/L40S) already carry a real bus width in the source, so the
loader uses that and this map never fires for them. When a curated value is
applied the row is marked `bandwidth_is_estimated = true`.

### Appendix C: `primary_domain` → `is_generative` / `throughput_unit`

| primary_domain | is_generative | throughput_unit |
|---|---|---|
| Language | yes | tokens/sec |
| Multimodal | yes | tokens/sec |
| Speech | yes | tokens/sec |
| Audio | yes | tokens/sec |
| Video | yes | tokens/sec |
| Image generation | yes | images/sec |
| Vision | no | NULL |
| Games | no | NULL |
| Biology | no | NULL |
| Robotics | no | NULL |
| Recommendation | no | NULL |
| Mathematics | no | NULL |
| Other / unresolved | no | NULL |

### Appendix D: Numeric assumptions

| Assumption | Value | Rationale |
|---|---|---|
| bytes per weight, fp16 / int8 / int4 | 2 / 1 / 0.5 | standard weight-storage sizes |
| runtime `OVERHEAD` factor | 1.20 | flat allowance for activations + KV cache + framework; deliberately coarse |
| real-world throughput derate | 0.50-0.75 of ceiling | attention over KV cache, kernel & sampling overhead; **not stored**, applied downstream if wanted |
| throughput model | `bandwidth / fp16_footprint` | autoregressive decoding is memory-bandwidth bound: every weight is read once per token. Sources: <https://inventivehq.com/blog/local-llm-performance-what-to-expect>, <https://www.spheron.network/blog/ai-memory-wall-inference-latency-guide-2026/> |

### Appendix E: Dataset provenance & caveats

- **Models:** Epoch AI *Notable AI Models* (`epoch.ai/data`), CC-BY. The repo copy
  (`csv/notable_ai_models.csv`, 1,052 rows) includes rows dated into 2026 and other
  synthetic/perturbed values; treated as-is for this academic exercise.
- **GPUs:** Kaggle `alanjo/graphics-card-full-specs` (TechPowerUp-derived),
  `csv/gpu_specs_v7.csv`, 3,056 rows. Contains a BOM header, ~77 % missing bus
  widths in the modern subset, dirty `memType` spellings, duplicate product names,
  and deliberately impossible chip/memory combinations, all handled in
  Section 6.2 and logged in the Phase 2 run summary.
- **Course reference:** M. Golfarelli, S. Rizzi, *Data Warehouse Design: Modern
  Principles and Methodologies*, McGraw-Hill 2009, `docs/lessons/DataWarehousing.pdf`.
