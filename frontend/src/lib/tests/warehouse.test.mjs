import test, { after } from "node:test";
import assert from "node:assert/strict";
import pg from "pg";
import { DEFAULT_GPU, parseFilters } from "../filters.mjs";
import {
  GPU_SQL,
  SUMMARY_SQL,
  TIMELINE_SQL,
  TRADEOFF_SQL,
  DOMAINS_SQL,
  modelQueries,
} from "../sql.mjs";

// Integration coverage is explicit: absent credentials or an unavailable DB fails this file.
assert.ok(
  process.env.POSTGRES_PASSWORD,
  "Run warehouse tests in the frontend Docker container with its database environment.",
);
const pool = new pg.Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  max: 2,
  connectionTimeoutMillis: 3000,
  statement_timeout: 10000,
  options: "-c default_transaction_read_only=on",
});
after(() => pool.end());
const rows = async (sql, values) => (await pool.query(sql, values)).rows;
const gpu = (await rows(GPU_SQL)).find((row) => row.key === DEFAULT_GPU);
assert.ok(gpu, "The real dataset must contain the default GPU.");
const summary = (await rows(SUMMARY_SQL, [gpu.id]))[0];

test("real warehouse contains the complete GPU × model cross product", async () => {
  const [counts] = await rows(
    `SELECT (SELECT count(*) FROM dim_gpu)::int AS gpus, (SELECT count(*) FROM dim_model)::int AS models, (SELECT count(*) FROM fact_gpu_model_compatibility)::int AS pairs`,
  );
  assert.ok(counts.gpus > 500);
  const [source] = await rows("SELECT count(*)::int AS total FROM ods.ods_models");
  assert.ok(counts.models > 0 && counts.models < source.total);
  assert.equal(counts.gpus * counts.models, counts.pairs);
  assert.equal(summary.total, counts.models);
  assert.equal(
    summary.fp16 +
      summary.int8 +
      summary.int4 +
      summary.too_large +
      summary.unknown,
    summary.total,
  );
  const validators = await rows("SELECT status FROM validator_fact_nulls");
  assert.equal(validators.length, 6);
  assert.ok(validators.every((row) => row.status === "pass"));
});
test("every compatibility filter agrees with real summary totals", async () => {
  for (const [status, expected] of Object.entries({
    all: summary.total,
    fp16: summary.fp16,
    quantized: summary.int8 + summary.int4,
    too_large: summary.too_large,
  })) {
    const filters = parseFilters({ status });
    const query = modelQueries(gpu.id, filters);
    assert.equal((await rows(query.count))[0].total, expected);
    const models = await rows(query.rows);
    for (const model of models) {
      if (status === "fp16") assert.ok(model.footprint <= gpu.vram);
      if (status === "quantized")
        assert.ok(
          model.footprint > gpu.vram &&
            model.footprint / (model.quantization === "8-bit" ? 2 : 4) <=
              gpu.vram,
        );
      if (status === "too_large") assert.ok(model.footprint / 4 > gpu.vram);
    }
  }
});
test("pagination is stable, disjoint, and honors domain and numeric sorting", async () => {
  const first = await rows(
    modelQueries(
      gpu.id,
      parseFilters({ domain: "Language", sort: "parameters" }),
    ).rows,
  );
  const second = await rows(
    modelQueries(
      gpu.id,
      parseFilters({ domain: "Language", sort: "parameters", page: "2" }),
    ).rows,
  );
  assert.equal(first.length, 25);
  assert.equal(new Set([...first, ...second].map((row) => row.id)).size, 50);
  assert.ok(first.every((row) => row.domain === "Language"));
  const values = [...first, ...second]
    .map((row) => row.parameters)
    .filter((value) => value != null);
  assert.ok(
    values.every((value, index) => index === 0 || value <= values[index - 1]),
  );
  assert.deepEqual(
    await rows(
      modelQueries(
        gpu.id,
        parseFilters({ domain: "Language", sort: "parameters" }),
      ).rows,
    ),
    first,
  );
});
test("SQL injection and literal wildcard searches cannot broaden results", async () => {
  for (const q of ["' OR 1=1; --", "zzzz-no-model-should-match-zzzz"])
    assert.equal(
      (await rows(modelQueries(gpu.id, parseFilters({ q })).count))[0].total,
      0,
    );
  const q = "%";
  const expected = (
    await rows(
      "SELECT count(*)::int AS total FROM dim_model WHERE strpos(model_name, '%') > 0 OR strpos(organization, '%') > 0",
    )
  )[0].total;
  assert.equal(
    (await rows(modelQueries(gpu.id, parseFilters({ q })).count))[0].total,
    expected,
  );
});
test("timeline uses known pairs as denominator, agrees with direct facts", async () => {
  const actual = (await rows(TIMELINE_SQL)).find(
    (row) =>
      row.architecture === gpu.architecture && row.known > 0 && row.rate < 100,
  );
  assert.ok(actual);
  const [expected] = await rows(
    `SELECT COUNT(*) FILTER (WHERE f.fits_in_vram)::int AS fits, COUNT(f.fits_in_vram)::int AS known, AVG(f.vram_headroom_gb)::float8 AS headroom FROM fact_gpu_model_compatibility f JOIN dim_gpu g USING(gpu_key) JOIN dim_model m USING(model_key) WHERE g.gpu_architecture=$1 AND m.release_year=$2`,
    [actual.architecture, actual.year],
  );
  assert.equal(actual.known, expected.known);
  assert.equal(actual.fits, expected.fits);
  assert.ok(
    Math.abs(actual.rate - (expected.fits / expected.known) * 100) < 0.000001,
  );
  assert.ok(Math.abs(actual.headroom - expected.headroom) < 0.000001);
});
test("VRAM trade-off counts distinct modern Language models and weighted average memory", async () => {
  const actual = (await rows(TRADEOFF_SQL)).find(
    (row) =>
      row.architecture === gpu.architecture &&
      row.vram_bucket === gpu.vram_bucket,
  );
  assert.ok(actual);
  const [expected] = await rows(
    `SELECT COUNT(DISTINCT model_key)::int AS models FROM fact_gpu_model_compatibility WHERE fits_in_vram AND gpu_key IN (SELECT gpu_key FROM dim_gpu WHERE gpu_architecture=$1 AND vram_bucket=$2) AND model_key IN (SELECT model_key FROM dim_model WHERE primary_domain='Language' AND release_year>=2020)`,
    [gpu.architecture, gpu.vram_bucket],
  );
  const [memory] = await rows(
    "SELECT AVG(vram_gb)::float8 AS vram FROM dim_gpu WHERE gpu_architecture=$1 AND vram_bucket=$2",
    [gpu.architecture, gpu.vram_bucket],
  );
  assert.equal(actual.models, expected.models);
  assert.ok(Math.abs(actual.vram - memory.vram) < 0.000001);
  assert.ok(
    Math.abs(actual.efficiency - expected.models / memory.vram) < 0.000001,
  );
});
test("domain accessibility excludes unknowns and counts fits on at least one GPU", async () => {
  const actual = (await rows(DOMAINS_SQL)).find(
    (row) => row.domain === "Language" && row.vram_bucket === gpu.vram_bucket,
  );
  const [expected] = await rows(
    `SELECT COUNT(DISTINCT f.model_key)::int AS total, COUNT(DISTINCT f.model_key) FILTER (WHERE f.quantization_required='none')::int AS fits FROM fact_gpu_model_compatibility f JOIN dim_gpu g USING(gpu_key) JOIN dim_model m USING(model_key) WHERE m.primary_domain='Language' AND g.vram_bucket=$1 AND f.quantization_required IS NOT NULL`,
    [gpu.vram_bucket],
  );
  assert.equal(actual.total, expected.total);
  assert.equal(actual.fits, expected.fits);
  assert.ok(
    Math.abs(actual.rate - (expected.fits / expected.total) * 100) < 0.000001,
  );
});
