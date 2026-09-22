-- DICE: generative models released after 2022 x GPUs with >= 24GB VRAM,
-- fit-rate and quantization mix.
SELECT
    g.vram_bucket,
    m.parameter_bucket,
    count(*)                                                             AS pairs,
    round(100.0 * count(*) FILTER (WHERE f.fits_in_vram) / count(*), 1)  AS pct_fit,
    count(*) FILTER (WHERE f.quantization_required = 'does-not-fit')     AS does_not_fit
FROM fact_gpu_model_compatibility f
JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
JOIN dim_model m ON m.model_key = f.model_key
WHERE m.is_generative
  AND m.release_year > 2022
  AND g.vram_gb >= 24
GROUP BY g.vram_bucket, m.parameter_bucket
ORDER BY g.vram_bucket, m.parameter_bucket;
