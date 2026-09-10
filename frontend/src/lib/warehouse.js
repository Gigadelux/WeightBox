import "server-only";
import { cache } from "react";
import { getPool } from "./db";
import { parseFilters, PAGE_SIZE } from "./filters.mjs";
import {
  GPU_SQL,
  SUMMARY_SQL,
  TIMELINE_SQL,
  TRADEOFF_SQL,
  DOMAINS_SQL,
  modelQueries,
} from "./sql.mjs";

const rows = async (query, values) =>
  (await getPool().query(query, values)).rows;
// Request-local deduplication only: refreshed ETL data is visible on the next request.
export const getCatalog = cache(async () => {
  const [gpus, domains] = await Promise.all([
    rows(GPU_SQL),
    rows(
      "SELECT DISTINCT primary_domain AS name FROM dim_model ORDER BY primary_domain",
    ),
  ]);
  if (!gpus.length || !domains.length) throw new Error("Warehouse is empty");
  return { gpus, domains: domains.map((row) => row.name) };
});
export async function getWorkbench(params) {
  const filters = parseFilters(params);
  const catalog = await getCatalog();
  const gpu = catalog.gpus.find((item) => item.key === filters.gpu);
  if (!gpu) return { ...catalog, filters, gpu: null };
  const [summary, count] = await Promise.all([
    rows(SUMMARY_SQL, [gpu.id]),
    rows(modelQueries(gpu.id, filters).count),
  ]);
  if (!summary[0]?.total) throw new Error("Compatibility data is empty");
  const pages = Math.max(1, Math.ceil(count[0].total / PAGE_SIZE));
  filters.page = Math.min(filters.page, pages);
  const models = await rows(modelQueries(gpu.id, filters).rows);
  return {
    ...catalog,
    filters,
    gpu,
    summary: summary[0],
    models,
    total: count[0].total,
    pages,
  };
}
export async function getAnalytics() {
  const results = await Promise.allSettled([
    rows(TIMELINE_SQL),
    rows(TRADEOFF_SQL),
    rows(DOMAINS_SQL),
  ]);
  return Object.fromEntries(
    ["timeline", "tradeoff", "domains"].map((name, i) => {
      if (results[i].status === "rejected")
        console.error(`WeightBox: ${name} data is unavailable`);
      return [
        name,
        results[i].status === "fulfilled" ? results[i].value : null,
      ];
    }),
  );
}
export async function getDataSummary() {
  const [counts, loads, validators, domains] = await Promise.all([
    rows(`SELECT (SELECT count(*)::int FROM dim_gpu) AS gpus, (SELECT count(*)::int FROM dim_model) AS models,
      (SELECT count(*)::int FROM fact_gpu_model_compatibility) AS pairs,
      (SELECT count(*)::int FROM dim_model WHERE parameter_count IS NULL) AS unknown,
      (SELECT count(*)::int FROM dim_gpu WHERE bandwidth_is_estimated) AS estimated,
      (SELECT count(*)::int FROM dim_gpu WHERE specs_suspect) AS suspect`),
    rows(`SELECT DISTINCT ON (ods_table) ods_table, file_name, row_count, loaded_at::text
      FROM ods.load_audit ORDER BY ods_table, loaded_at DESC, load_id DESC`),
    rows(
      "SELECT attribute, status, null_count::int, not_null_count::int, checked_at::text FROM validator_fact_nulls ORDER BY attribute",
    ),
    rows(
      "SELECT primary_domain AS name, count(*)::int AS total FROM dim_model GROUP BY primary_domain ORDER BY total DESC, primary_domain",
    ),
  ]);
  if (!counts[0].gpus || !counts[0].models || !counts[0].pairs)
    throw new Error("Warehouse is empty");
  return { ...counts[0], loads, validators, domains };
}
