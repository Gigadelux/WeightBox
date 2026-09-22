-- DRILL-DOWN: same roll-up one level lower, by parameter_bucket within the
-- most populous gpu_architecture.
SELECT
    g.gpu_architecture,
    m.parameter_bucket,
    count(*) FILTER (WHERE f.fits_in_vram)                    AS models_deployable,
    round(avg(f.estimated_throughput), 2)                     AS avg_throughput,
    min(f.estimated_throughput)                                AS min_throughput,
    max(f.estimated_throughput)                                AS max_throughput
FROM fact_gpu_model_compatibility f
JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
JOIN dim_model m ON m.model_key = f.model_key
WHERE g.gpu_architecture = (
    SELECT gpu_architecture FROM dim_gpu
    GROUP BY gpu_architecture ORDER BY count(*) DESC LIMIT 1
)
GROUP BY g.gpu_architecture, m.parameter_bucket
ORDER BY m.parameter_bucket;
