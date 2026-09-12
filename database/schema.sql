-- WeightBox ROLAP data warehouse
-- Generated reference of the schema the ETL builds (etl/SQL/tables/*.py is the
-- source of truth; this file is not executed). Regenerate after schema changes.

CREATE SCHEMA IF NOT EXISTS ods;

CREATE TABLE IF NOT EXISTS ods.ods_models (
    ods_model_id bigint GENERATED ALWAYS AS IDENTITY,
    model text,
    organization text,
    publication_date text,
    domain text,
    task text,
    parameters text,
    parameters_notes text,
    training_compute_flop text,
    training_compute_notes text,
    training_dataset text,
    training_dataset_size_total text,
    dataset_size_notes text,
    confidence text,
    link text,
    reference text,
    citations text,
    authors text,
    abstract text,
    organization_categorization text,
    country_of_organization text,
    notability_criteria text,
    notability_criteria_notes text,
    epochs text,
    training_time_hours text,
    training_time_notes text,
    training_hardware text,
    hardware_quantity text,
    hardware_utilization_mfu text,
    training_compute_cost_2023_usd text,
    compute_cost_notes text,
    training_power_draw_w text,
    base_model text,
    finetune_compute_flop text,
    finetune_compute_notes text,
    batch_size text,
    batch_size_notes text,
    model_accessibility text,
    training_code_accessibility text,
    inference_code_accessibility text,
    accessibility_notes text,
    numerical_format text,
    frontier_model text,
    hardware_acquisition_cost text,
    hardware_utilization_hfu text,
    training_compute_cost_cloud text,
    training_compute_cost_upfront text,
    open_model_weights text,
    _source_sha256 text NOT NULL,
    _loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ods_model_id)
);

CREATE TABLE IF NOT EXISTS ods.ods_gpus (
    ods_gpu_id bigint GENERATED ALWAYS AS IDENTITY,
    manufacturer text,
    product_name text,
    release_year text,
    mem_size text,
    mem_bus_width text,
    gpu_clock text,
    mem_clock text,
    unified_shader text,
    tmu text,
    rop text,
    pixel_shader text,
    vertex_shader text,
    igp text,
    bus text,
    mem_type text,
    gpu_chip text,
    _source_sha256 text NOT NULL,
    _loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ods_gpu_id)
);

CREATE TABLE IF NOT EXISTS ods.load_audit (
    load_id bigint GENERATED ALWAYS AS IDENTITY,
    ods_table text NOT NULL,
    file_name text NOT NULL,
    sha256 text NOT NULL,
    row_count integer NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (load_id)
);

CREATE TABLE IF NOT EXISTS ods.profile_log (
    profile_id bigint GENERATED ALWAYS AS IDENTITY,
    ods_table text NOT NULL,
    column_name text NOT NULL,
    total_rows integer NOT NULL,
    empty_count integer NOT NULL,
    empty_rate numeric NOT NULL,
    profiled_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (profile_id)
);

CREATE TABLE IF NOT EXISTS ods.reject_models (
    reject_id bigint GENERATED ALWAYS AS IDENTITY,
    natural_key text,
    rule text NOT NULL,
    detail text,
    rejected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (reject_id)
);

CREATE TABLE IF NOT EXISTS ods.reject_gpus (
    reject_id bigint GENERATED ALWAYS AS IDENTITY,
    natural_key text,
    rule text NOT NULL,
    detail text,
    rejected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (reject_id)
);

CREATE TABLE IF NOT EXISTS public.dim_model (
    model_key bigint GENERATED ALWAYS AS IDENTITY,
    model_nk text NOT NULL UNIQUE,
    model_name text NOT NULL,
    organization text NOT NULL DEFAULT 'Unknown',
    organization_country text NOT NULL DEFAULT 'Unknown',
    primary_domain text NOT NULL,
    is_generative boolean NOT NULL,
    throughput_unit text,
    parameter_count numeric,
    parameter_count_is_estimated boolean NOT NULL DEFAULT false,
    parameter_bucket text NOT NULL,
    training_compute_flop numeric,
    release_date date NOT NULL,
    release_month smallint NOT NULL,
    release_quarter smallint NOT NULL,
    release_year smallint NOT NULL,
    release_decade smallint NOT NULL,
    confidence text,
    source_dataset text NOT NULL DEFAULT 'notable_ai_models',
    PRIMARY KEY (model_key)
);

CREATE TABLE IF NOT EXISTS public.dim_gpu (
    gpu_key bigint GENERATED ALWAYS AS IDENTITY,
    gpu_nk text NOT NULL UNIQUE,
    product_name text NOT NULL,
    manufacturer text NOT NULL,
    gpu_chip text,
    gpu_architecture text NOT NULL DEFAULT 'Unknown',
    release_year smallint,
    vram_gb numeric NOT NULL,
    vram_bucket text NOT NULL,
    mem_bus_width_bit integer,
    mem_clock_mhz numeric,
    mem_type text NOT NULL,
    mem_family text NOT NULL,
    data_rate numeric NOT NULL,
    memory_bandwidth_gbs numeric NOT NULL,
    bandwidth_is_estimated boolean NOT NULL DEFAULT false,
    specs_suspect boolean NOT NULL DEFAULT false,
    PRIMARY KEY (gpu_key)
);

CREATE TABLE IF NOT EXISTS public.fact_gpu_model_compatibility (
    gpu_key bigint NOT NULL REFERENCES dim_gpu(gpu_key),
    model_key bigint NOT NULL REFERENCES dim_model(model_key),
    model_nk text NOT NULL,
    gpu_nk text NOT NULL,
    model_vram_footprint_gb numeric,
    fits_in_vram boolean,
    vram_headroom_gb numeric,
    quantization_required text,
    estimated_throughput numeric,
    throughput_unit varchar,
    PRIMARY KEY (gpu_key, model_key)
);

CREATE TABLE IF NOT EXISTS public.validator_fact_nulls (
    attribute text NOT NULL,
    null_allowed boolean NOT NULL,
    null_rule text NOT NULL,
    null_count bigint,
    not_null_count bigint,
    total_rows bigint,
    status text NOT NULL DEFAULT 'pending',
    detail text,
    checked_at timestamptz,
    PRIMARY KEY (attribute)
);


CREATE MATERIALIZED VIEW IF NOT EXISTS mv_deployability_by_year_arch AS
SELECT m.release_year,
       g.gpu_architecture,
       count(*)                                AS pairs,
       count(*) FILTER (WHERE f.fits_in_vram)  AS pairs_fit,
       sum(f.vram_headroom_gb)                 AS sum_headroom_gb,
       count(f.vram_headroom_gb)               AS n_headroom
FROM   fact_gpu_model_compatibility f
JOIN   dim_model m ON m.model_key = f.model_key
JOIN   dim_gpu   g ON g.gpu_key   = f.gpu_key
GROUP BY m.release_year, g.gpu_architecture;



CREATE MATERIALIZED VIEW IF NOT EXISTS mv_gpu_generation_tradeoff AS
SELECT g.gpu_architecture,
       m.parameter_bucket,
       count(DISTINCT f.model_key) FILTER (WHERE f.fits_in_vram) AS models_deployable,
       sum(f.estimated_throughput)                              AS sum_throughput,
       count(f.estimated_throughput)                            AS n_throughput,
       min(f.estimated_throughput)                              AS min_throughput,
       max(f.estimated_throughput)                              AS max_throughput
FROM   fact_gpu_model_compatibility f
JOIN   dim_model m ON m.model_key = f.model_key
JOIN   dim_gpu   g ON g.gpu_key   = f.gpu_key
GROUP BY g.gpu_architecture, m.parameter_bucket;



CREATE MATERIALIZED VIEW IF NOT EXISTS mv_domain_accessibility AS
SELECT m.primary_domain,
       g.vram_bucket,
       count(DISTINCT f.model_key)                                                AS models_total,
       count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = 'none') AS models_no_quant,
       count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = '8-bit') AS models_8bit,
       count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = '4-bit') AS models_4bit
FROM   fact_gpu_model_compatibility f
JOIN   dim_model m ON m.model_key = f.model_key
JOIN   dim_gpu   g ON g.gpu_key   = f.gpu_key
WHERE  f.quantization_required IS NOT NULL
GROUP BY m.primary_domain, g.vram_bucket;

-- Indexes (Phase 3)

CREATE INDEX IF NOT EXISTS ix_fact_model_nk ON fact_gpu_model_compatibility (model_nk);
CREATE INDEX IF NOT EXISTS ix_fact_gpu_nk ON fact_gpu_model_compatibility (gpu_nk);
CREATE INDEX IF NOT EXISTS ix_fact_gpu_key ON fact_gpu_model_compatibility (gpu_key);
CREATE INDEX IF NOT EXISTS ix_fact_model_key ON fact_gpu_model_compatibility (model_key);
CREATE INDEX IF NOT EXISTS ix_fact_model_key_fits ON fact_gpu_model_compatibility (model_key) WHERE fits_in_vram;
CREATE INDEX IF NOT EXISTS ix_dim_model_primary_domain ON dim_model (primary_domain);
CREATE INDEX IF NOT EXISTS ix_dim_model_release_year ON dim_model (release_year);
CREATE INDEX IF NOT EXISTS ix_dim_gpu_architecture ON dim_gpu (gpu_architecture);
CREATE INDEX IF NOT EXISTS ix_dim_gpu_vram_bucket ON dim_gpu (vram_bucket);
