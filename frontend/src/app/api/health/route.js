import { getPool } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { rows } = await getPool().query(`
      SELECT
        EXISTS (SELECT 1 FROM dim_gpu) AND
        EXISTS (SELECT 1 FROM dim_model) AND
        EXISTS (SELECT 1 FROM fact_gpu_model_compatibility) AND
        (SELECT count(*) = 6 AND bool_and(status = 'pass') FROM validator_fact_nulls) AND
        EXISTS (SELECT 1 FROM mv_deployability_by_year_arch) AND
        EXISTS (SELECT 1 FROM mv_gpu_generation_tradeoff) AND
        EXISTS (SELECT 1 FROM mv_domain_accessibility) AS ready
    `);
    if (rows[0]?.ready) {
      return Response.json({ status: "ok", database: "ready" });
    }
  } catch {
    // Health responses must not expose database URLs or internal error details.
  }
  return Response.json(
    { status: "unavailable", database: "unavailable_or_uninitialized" },
    { status: 503 },
  );
}
