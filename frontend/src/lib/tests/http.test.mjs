import test from "node:test";
import assert from "node:assert/strict";

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
  assert.ok(markup.includes("Page 1 of 43"));
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
  assert.ok((await page("/?status=unknown")).markup.includes("348 matching"));
  const second = (await page("/?page=2")).markup;
  assert.ok(second.includes("Page 2 of 43"));
  const last = (await page("/?page=99999")).markup;
  assert.ok(last.includes("Page 43 of 43"));
  const alternate = (
    await page(
      "/?gpu=GeForce%20RTX%204090%7C2022&domain=Vision&sort=parameters",
    )
  ).markup;
  assert.ok(alternate.includes("205 matching"));
});
test("methodology and dataset pages render and the warehouse is ready", async () => {
  assert.ok((await page("/methodology")).markup.includes("bytes per weight"));
  const { markup } = await page("/data");
  for (const value of ["649,084", "617", "1,052", "6 / 6 checks passed"])
    assert.ok(markup.includes(value), `Dataset missing ${value}`);
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
