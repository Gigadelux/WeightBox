-- SLICE: fix primary_domain = 'Language', aggregate accessibility across
-- vram_bucket. Matches mv_domain_accessibility's own row filter so counts are
-- directly comparable to that view.
SELECT
    g.vram_bucket,
    count(DISTINCT f.model_key)                                                  AS models_total,
    count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = 'none')  AS models_no_quant,
    count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = '8-bit') AS models_8bit,
    count(DISTINCT f.model_key) FILTER (WHERE f.quantization_required = '4-bit') AS models_4bit
FROM fact_gpu_model_compatibility f
JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
JOIN dim_model m ON m.model_key = f.model_key
WHERE m.primary_domain = 'Language'
  AND f.quantization_required IS NOT NULL
GROUP BY g.vram_bucket
ORDER BY g.vram_bucket;
