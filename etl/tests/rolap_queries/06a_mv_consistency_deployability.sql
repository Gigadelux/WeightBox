-- MV CONSISTENCY: mv_deployability_by_year_arch vs a live re-aggregation of
-- the star schema, using the view's own GROUP BY from etl/SQL/tables/views.py.
WITH live AS (
    SELECT m.release_year, g.gpu_architecture,
           count(*)                                AS pairs,
           count(*) FILTER (WHERE f.fits_in_vram)   AS pairs_fit,
           sum(f.vram_headroom_gb)                  AS sum_headroom_gb,
           count(f.vram_headroom_gb)                AS n_headroom
    FROM fact_gpu_model_compatibility f
    JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
    JOIN dim_model m ON m.model_key = f.model_key
    GROUP BY m.release_year, g.gpu_architecture
)
SELECT
    count(*) AS mv_rows,
    (SELECT count(*) FROM live) AS live_rows,
    count(*) FILTER (
        WHERE mv.pairs <> l.pairs OR mv.pairs_fit <> l.pairs_fit
    ) AS mismatched_rows
FROM mv_deployability_by_year_arch mv
JOIN live l USING (release_year, gpu_architecture);
