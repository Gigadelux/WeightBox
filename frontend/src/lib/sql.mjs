import { escapeLike, PAGE_SIZE } from "./filters.mjs";

const statusPredicates = {
  fp16: "f.quantization_required = 'none'",
  quantized: "f.quantization_required IN ('8-bit', '4-bit')",
  too_large: "f.quantization_required = 'does-not-fit'",
  unknown: "f.quantization_required IS NULL",
};
const orders = {
  compatibility:
    "CASE f.quantization_required WHEN 'none' THEN 0 WHEN '8-bit' THEN 1 WHEN '4-bit' THEN 2 WHEN 'does-not-fit' THEN 3 ELSE 4 END, m.model_name",
  name: "m.model_name",
  parameters: "m.parameter_count DESC NULLS LAST, m.model_name",
  footprint: "f.model_vram_footprint_gb ASC NULLS LAST, m.model_name",
  newest: "m.release_date DESC, m.model_name",
};
export function modelQueries(gpuKey, filters, page = filters.page) {
  const values = [gpuKey];
  const where = ["f.gpu_key = $1"];
  if (filters.q) {
    values.push(`%${escapeLike(filters.q)}%`);
    where.push(
      `(m.model_name ILIKE $${values.length} OR m.organization ILIKE $${values.length})`,
    );
  }
  if (filters.domain) {
    values.push(filters.domain);
    where.push(`m.primary_domain = $${values.length}`);
  }
  if (Object.hasOwn(statusPredicates, filters.status))
    where.push(statusPredicates[filters.status]);
  const from = `FROM fact_gpu_model_compatibility f JOIN dim_model m USING (model_key) WHERE ${where.join(" AND ")}`;
  return {
    count: { text: `SELECT count(*)::int AS total ${from}`, values },
    rows: {
      text: `SELECT m.model_key::text AS id, m.model_name AS name, m.organization, m.primary_domain AS domain,
        m.parameter_count::float8 AS parameters, m.release_year AS year, m.is_generative,
        f.model_vram_footprint_gb::float8 AS footprint, f.vram_headroom_gb::float8 AS headroom,
        f.quantization_required AS quantization, f.estimated_throughput::float8 AS throughput, f.throughput_unit
        ${from} ORDER BY ${Object.hasOwn(orders, filters.sort) ? orders[filters.sort] : orders.compatibility}, m.model_key
        LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      values: [...values, PAGE_SIZE, (page - 1) * PAGE_SIZE],
    },
  };
}
export const GPU_SQL = `SELECT gpu_key::text AS id, gpu_nk AS key, product_name AS name, manufacturer,
  gpu_architecture AS architecture, release_year AS year, vram_gb::float8 AS vram, vram_bucket,
  mem_type AS memory, mem_bus_width_bit AS bus, memory_bandwidth_gbs::float8 AS bandwidth,
  bandwidth_is_estimated AS estimated, specs_suspect AS suspect
  FROM dim_gpu ORDER BY manufacturer, product_name, gpu_key`;
export const SUMMARY_SQL = `SELECT count(*)::int AS total,
  count(*) FILTER (WHERE quantization_required = 'none')::int AS fp16,
  count(*) FILTER (WHERE quantization_required = '8-bit')::int AS int8,
  count(*) FILTER (WHERE quantization_required = '4-bit')::int AS int4,
  count(*) FILTER (WHERE quantization_required = 'does-not-fit')::int AS too_large,
  count(*) FILTER (WHERE quantization_required IS NULL)::int AS unknown
  FROM fact_gpu_model_compatibility WHERE gpu_key = $1`;
export const TIMELINE_SQL = `SELECT release_year AS year, gpu_architecture AS architecture,
  SUM(pairs_fit)::int AS fits, SUM(n_headroom)::int AS known,
  (100.0 * SUM(pairs_fit) / NULLIF(SUM(n_headroom), 0))::float8 AS rate,
  (SUM(sum_headroom_gb) / NULLIF(SUM(n_headroom), 0))::float8 AS headroom
  FROM mv_deployability_by_year_arch GROUP BY release_year, gpu_architecture ORDER BY release_year, gpu_architecture`;
// The generation MV groups by parameter bucket, not VRAM; this follows specs §7.2 directly.
export const TRADEOFF_SQL = `SELECT g.gpu_architecture AS architecture, g.vram_bucket,
  AVG(g.vram_gb)::float8 AS vram,
  COUNT(DISTINCT f.model_key) FILTER (WHERE f.fits_in_vram)::int AS models,
  (COUNT(DISTINCT f.model_key) FILTER (WHERE f.fits_in_vram) / NULLIF(AVG(g.vram_gb), 0))::float8 AS efficiency
  FROM fact_gpu_model_compatibility f JOIN dim_gpu g USING (gpu_key) JOIN dim_model m USING (model_key)
  WHERE m.primary_domain = 'Language' AND m.release_year >= 2020
  GROUP BY g.gpu_architecture, g.vram_bucket ORDER BY efficiency DESC, g.gpu_architecture, g.vram_bucket`;
export const DOMAINS_SQL = `SELECT primary_domain AS domain, vram_bucket, models_total::int AS total,
  models_no_quant::int AS fits, (100.0 * models_no_quant / NULLIF(models_total, 0))::float8 AS rate
  FROM mv_domain_accessibility ORDER BY primary_domain, vram_bucket`;
