-- MV CONSISTENCY: mv_gpu_generation_tradeoff vs a live re-aggregation of the
-- star schema, using the view's own GROUP BY from etl/SQL/tables/views.py.
-- models_deployable is COUNT(DISTINCT model_key), matching the view exactly.
WITH live AS (
    SELECT g.gpu_architecture, m.parameter_bucket,
           count(DISTINCT f.model_key) FILTER (WHERE f.fits_in_vram) AS models_deployable,
           sum(f.estimated_throughput)                               AS sum_throughput,
           count(f.estimated_throughput)                             AS n_throughput
    FROM fact_gpu_model_compatibility f
    JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
    JOIN dim_model m ON m.model_key = f.model_key
    GROUP BY g.gpu_architecture, m.parameter_bucket
)
SELECT
    count(*) AS mv_rows,
    (SELECT count(*) FROM live) AS live_rows,
    count(*) FILTER (
        WHERE mv.models_deployable <> l.models_deployable OR mv.n_throughput <> l.n_throughput
    ) AS mismatched_rows
FROM mv_gpu_generation_tradeoff mv
JOIN live l USING (gpu_architecture, parameter_bucket);
