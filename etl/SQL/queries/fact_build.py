"""The set-based fact build (WEIGHTBOX_SPECS.md section 6.4).

One INSERT ... SELECT over dim_gpu CROSS JOIN dim_model. The LATERAL block
computes the three quantised footprints once per pair; %(overhead)s is the
runtime overhead factor from Appendix D.
"""

from __future__ import annotations

TRUNCATE_STAR = (
    "TRUNCATE fact_gpu_model_compatibility, dim_gpu, dim_model RESTART IDENTITY CASCADE;"
)

INSERT_FACT = """
INSERT INTO fact_gpu_model_compatibility
    (gpu_key, model_key, model_nk, gpu_nk,
     model_vram_footprint_gb, fits_in_vram, vram_headroom_gb,
     quantization_required, estimated_throughput, throughput_unit)
SELECT
    g.gpu_key,
    m.model_key,
    m.model_nk,
    g.gpu_nk,
    fp.footprint_fp16,
    (fp.footprint_fp16 <= g.vram_gb)            AS fits_in_vram,
    (g.vram_gb - fp.footprint_fp16)             AS vram_headroom_gb,
    CASE
      WHEN m.parameter_count IS NULL     THEN NULL
      WHEN fp.footprint_fp16 <= g.vram_gb THEN 'none'
      WHEN fp.footprint_int8 <= g.vram_gb THEN '8-bit'
      WHEN fp.footprint_int4 <= g.vram_gb THEN '4-bit'
      ELSE 'does-not-fit'
    END                                        AS quantization_required,
    CASE
      WHEN m.is_generative
       AND m.parameter_count IS NOT NULL
       AND g.memory_bandwidth_gbs IS NOT NULL
      THEN g.memory_bandwidth_gbs / NULLIF(fp.footprint_fp16, 0)
    END                                        AS estimated_throughput,
    CASE
      WHEN m.is_generative
       AND m.parameter_count IS NOT NULL
       AND g.memory_bandwidth_gbs IS NOT NULL
      THEN m.throughput_unit
    END                                        AS throughput_unit
FROM dim_gpu g
CROSS JOIN dim_model m
LEFT JOIN LATERAL (
    SELECT
      m.parameter_count * 2   * %(overhead)s / 1e9 AS footprint_fp16,
      m.parameter_count * 1   * %(overhead)s / 1e9 AS footprint_int8,
      m.parameter_count * 0.5 * %(overhead)s / 1e9 AS footprint_int4
) fp ON true;
"""

# Post-load assertions (raise on non-zero / mismatch).
COUNT_FACT = "SELECT count(*) FROM fact_gpu_model_compatibility;"
COUNT_EXPECTED = (
    "SELECT (SELECT count(*) FROM dim_gpu) * (SELECT count(*) FROM dim_model);"
)
ORPHAN_FKS = """
SELECT count(*) FROM fact_gpu_model_compatibility f
LEFT JOIN dim_gpu   g ON g.gpu_key   = f.gpu_key
LEFT JOIN dim_model m ON m.model_key = f.model_key
WHERE g.gpu_key IS NULL OR m.model_key IS NULL;
"""
DOES_NOT_FIT_CONSISTENCY = """
SELECT count(*) FROM fact_gpu_model_compatibility
WHERE quantization_required = 'does-not-fit' AND fits_in_vram IS DISTINCT FROM false;
"""
NK_POPULATED = """
SELECT count(*) FROM fact_gpu_model_compatibility
WHERE model_nk IS NULL OR gpu_nk IS NULL;
"""
