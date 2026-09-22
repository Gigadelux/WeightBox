-- MV CONSISTENCY: mv_domain_accessibility vs a live re-aggregation of the
-- star schema, using the view's own GROUP BY and WHERE from
-- etl/SQL/tables/views.py.
WITH live AS (
    SELECT m.primary_domain, g.vram_bucket,
           count(DISTINCT m.model_key)                                                 AS models_total,
           count(DISTINCT m.model_key) FILTER (WHERE f.quantization_required = 'none') AS models_no_quant,
           count(DISTINCT m.model_key) FILTER (WHERE f.quantization_required = '8-bit') AS models_8bit,
           count(DISTINCT m.model_key) FILTER (WHERE f.quantization_required = '4-bit') AS models_4bit
    FROM fact_gpu_model_compatibility f
    JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
    JOIN dim_model m ON m.model_key = f.model_key
    WHERE f.quantization_required IS NOT NULL
    GROUP BY m.primary_domain, g.vram_bucket
)
SELECT
    count(*) AS mv_rows,
    (SELECT count(*) FROM live) AS live_rows,
    count(*) FILTER (
        WHERE mv.models_total <> l.models_total
    ) AS mismatched_rows
FROM mv_domain_accessibility mv
JOIN live l USING (primary_domain, vram_bucket);
