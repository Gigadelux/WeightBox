"""The three materialized views for the proposal's OLAP analyses.

Each stores COUNT and SUM (and MIN/MAX where distributive) rather than AVG, so a
further roll-up recomputes correct averages (WEIGHTBOX_SPECS.md section 7.4).
"""

from __future__ import annotations

MV_DEPLOYABILITY_BY_YEAR_ARCH = """
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
"""

MV_GPU_GENERATION_TRADEOFF = """
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
"""

MV_DOMAIN_ACCESSIBILITY = """
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
"""

VIEW_DDL: dict[str, str] = {
    "mv_deployability_by_year_arch": MV_DEPLOYABILITY_BY_YEAR_ARCH,
    "mv_gpu_generation_tradeoff": MV_GPU_GENERATION_TRADEOFF,
    "mv_domain_accessibility": MV_DOMAIN_ACCESSIBILITY,
}
