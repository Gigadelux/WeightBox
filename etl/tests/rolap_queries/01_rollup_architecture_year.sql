-- ROLL-UP: pairs / fit-rate / avg headroom by gpu_architecture x release_year.
SELECT
    g.gpu_architecture,
    m.release_year,
    count(*)                                  AS pairs,
    count(*) FILTER (WHERE f.fits_in_vram)    AS pairs_fit,
    round(avg(f.vram_headroom_gb), 2)         AS avg_headroom_gb
FROM fact_gpu_model_compatibility f
JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
JOIN dim_model m ON m.model_key = f.model_key
GROUP BY ROLLUP (g.gpu_architecture, m.release_year)
ORDER BY g.gpu_architecture NULLS LAST, m.release_year NULLS LAST
LIMIT 20;
