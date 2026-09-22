-- PIVOT: mem_type (rows) x parameter_bucket (columns), fits_in_vram counts.
SELECT
    g.mem_type,
    count(*) FILTER (WHERE m.parameter_bucket = '1-7B'    AND f.fits_in_vram) AS "1-7B",
    count(*) FILTER (WHERE m.parameter_bucket = '7-13B'   AND f.fits_in_vram) AS "7-13B",
    count(*) FILTER (WHERE m.parameter_bucket = '13-34B'  AND f.fits_in_vram) AS "13-34B",
    count(*) FILTER (WHERE m.parameter_bucket = '34-70B'  AND f.fits_in_vram) AS "34-70B",
    count(*) FILTER (WHERE m.parameter_bucket = '70-180B' AND f.fits_in_vram) AS "70-180B",
    count(*) FILTER (WHERE m.parameter_bucket = '>180B'   AND f.fits_in_vram) AS ">180B"
FROM fact_gpu_model_compatibility f
JOIN dim_gpu g   ON g.gpu_key = f.gpu_key
JOIN dim_model m ON m.model_key = f.model_key
GROUP BY g.mem_type
ORDER BY g.mem_type;
