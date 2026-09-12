import test, { after } from "node:test";
import assert from "node:assert/strict";
import pg from "pg";
import { DEFAULT_GPU, PAGE_SIZE } from "../filters.mjs";

const pool = new pg.Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT || 5432),
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  options: "-c default_transaction_read_only=on",
});
after(() => pool.end());
const { rows: [counts] } = await pool.query(`SELECT
  (SELECT count(*)::int FROM dim_model) AS models,
  (SELECT count(*)::int FROM dim_gpu) AS gpus,
  (SELECT count(*)::int FROM fact_gpu_model_compatibility) AS pairs,
  (SELECT count(*)::int FROM dim_model WHERE primary_domain = 'Vision') AS vision`);
const pages = Math.ceil(counts.models / PAGE_SIZE);

const origin = process.env.WEIGHTBOX_TEST_URL || "http://localhost:3000";
async function page(path) {
  const response = await fetch(origin + path);
  const html = await response.text();
  assert.equal(response.status, 200, `Expected a rendered page at ${path}`);
  // Inspect server-rendered HTML, excluding the serialized React payload.
  const markup = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
  return { html, markup: markup.replace(/<[^>]*>/g, "") };
}
test("production workbench renders real hardware, results, and all comparisons", async () => {
  const { html, markup } = await page("/");
  for (const text of [
    "GeForce RTX 4090",
    "Meet your next model",
    "As models grow",
    "More memory",
    "A little room for every field",
  ])
    assert.ok(markup.includes(text), `Missing ${text}`);
  assert.equal((html.match(/class="model-name /g) || []).length, 25);
  assert.ok(markup.includes(`Page 1 of ${pages}`));
  assert.ok(markup.includes(`${counts.models.toLocaleString("en-US")} warehouse models evaluated`));
  assert.ok(markup.includes("Evaluation does not guarantee"));
  const summary = html.match(/<section\b[^>]*class="compatibility-summary[\s\S]*?<\/section>/)?.[0];
  assert.ok(summary, "Compatibility summary is rendered");
  assert.equal((summary.match(/class="summary-item /g) || []).length, 3);
  assert.doesNotMatch(summary, /Unknown|Parameter count missing/);
  assert.doesNotMatch(html, /<option[^>]*value="unknown"/);
  const widths = [...summary.matchAll(/style="width:([\d.]+)%"/g)].map((match) => Number(match[1]));
  assert.equal(widths.length, 3);
  assert.ok(Math.abs(widths.reduce((total, width) => total + width, 0) - 100) < 0.000001);
  const { rows: [expected] } = await pool.query(`SELECT
    count(*) FILTER (WHERE quantization_required = 'none')::int AS fp16,
    count(*) FILTER (WHERE quantization_required IN ('8-bit', '4-bit'))::int AS quantized,
    count(*) FILTER (WHERE quantization_required = 'does-not-fit')::int AS too_large,
    count(quantization_required)::int AS known
    FROM fact_gpu_model_compatibility JOIN dim_gpu g USING (gpu_key) WHERE g.gpu_nk = $1`, [DEFAULT_GPU]);
  for (const [i, key] of ["fp16", "quantized", "too_large"].entries())
    assert.ok(Math.abs(widths[i] - expected[key] / expected.known * 100) < 0.000001);
});
test("filters, empty search, invalid GPU, and pagination have distinct rendered states", async () => {
  assert.ok(
    (await page("/?q=zzzz-no-model-zzzz")).markup.includes(
      "No models on this shelf",
    ),
  );
  assert.ok(
    (await page("/?gpu=missing")).markup.includes(
      "This GPU isn’t in the dataset",
    ),
  );
  assert.ok((await page("/?status=unknown")).markup.includes(`Page 1 of ${pages}`));
  const second = (await page("/?page=2")).markup;
  assert.ok(second.includes(`Page 2 of ${pages}`));
  const last = (await page("/?page=99999")).markup;
  assert.ok(last.includes(`Page ${pages} of ${pages}`));
  const alternate = (
    await page(
      "/?gpu=GeForce%20RTX%204090%7C2022&domain=Vision&sort=parameters",
    )
  ).markup;
  assert.ok(alternate.includes(`${counts.vision.toLocaleString("en-US")} matching`));
});
test("methodology and dataset pages render and the warehouse is ready", async () => {
  assert.ok((await page("/methodology")).markup.includes("bytes per weight"));
  const { markup } = await page("/data");
  for (const value of [counts.pairs, counts.gpus, counts.models].map((value) => value.toLocaleString("en-US")).concat("6 / 6 checks passed"))
    assert.ok(markup.includes(value), `Dataset missing ${value}`);
  assert.match(markup, new RegExp(`AI models${counts.models.toLocaleString("en-US")}Retained in the warehouse`));
  assert.doesNotMatch(markup, /Models without parameter counts/);
  const response = await fetch(origin + "/api/health");
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: "ok", database: "ready" });
});
test("database credentials are absent from HTML and linked browser JavaScript/CSS", async () => {
  assert.ok(
    process.env.POSTGRES_PASSWORD,
    "Run this check in the frontend Docker container.",
  );
  const { html } = await page("/");
  const secrets = [process.env.POSTGRES_PASSWORD];
  for (const secret of secrets)
    assert.equal(html.includes(secret), false, "Credential appeared in HTML");
  const paths = [
    ...new Set(
      [
        ...html.matchAll(
          /(?:src|href)="(\/_next\/static\/[^\"]+\.(?:js|css)(?:\?[^\"]*)?)"/g,
        ),
      ].map((match) => match[1]),
    ),
  ];
  assert.ok(paths.length > 1, "Expected browser assets to inspect");
  for (const path of paths) {
    const response = await fetch(origin + path.replaceAll("&amp;", "&"));
    assert.equal(response.status, 200, "Browser asset failed to load");
    const asset = await response.text();
    for (const secret of secrets)
      assert.equal(
        asset.includes(secret),
        false,
        "Credential appeared in a browser asset",
      );
  }
});
