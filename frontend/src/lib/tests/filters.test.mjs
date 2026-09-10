import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_GPU,
  escapeLike,
  filterUrl,
  parseFilters,
} from "../filters.mjs";
import { compatibility, compact } from "../format.mjs";
import { modelQueries } from "../sql.mjs";

test("URL inputs reject repeated, unknown, prototype, and invalid pagination values", () => {
  const filters = parseFilters({
    gpu: ["bad", "worse"],
    q: " x ",
    status: "__proto__",
    sort: "constructor",
    page: "-2",
  });
  assert.equal(filters.gpu, DEFAULT_GPU);
  assert.equal(filters.q, "x");
  assert.equal(filters.status, "all");
  assert.equal(filters.sort, "compatibility");
  assert.equal(filters.page, 1);
  for (const page of ["NaN", "Infinity", "1.4", ["2", "3"]])
    assert.equal(parseFilters({ page }).page, 1);
  assert.equal(
    parseFilters({ q: "x".repeat(300), page: "999999999" }).q.length,
    120,
  );
  assert.equal(parseFilters({ page: "999999999" }).page, 100000);
});
test("URLs preserve stable GPU identity and restore filters across shares", () => {
  const filters = parseFilters({
    gpu: "GPU & Plus|2022",
    q: "a+b %",
    domain: "Image generation",
    status: "unknown",
    page: "3",
  });
  const url = filterUrl(filters);
  assert.deepEqual(
    parseFilters(
      Object.fromEntries(new URL(url, "http://localhost").searchParams),
    ),
    filters,
  );
  assert.equal(
    new URL(
      filterUrl(filters, { page: 1, q: "" }),
      "http://localhost",
    ).searchParams.has("q"),
    false,
  );
});
test("search binds SQL values and treats wildcard characters literally", () => {
  const attack = "' OR 1=1; --";
  const queries = modelQueries(
    "9",
    parseFilters({ q: attack, domain: "Vision", sort: attack }),
  );
  assert.equal(queries.rows.text.includes(attack), false);
  assert.ok(queries.rows.values.includes(`%${attack}%`));
  assert.equal(escapeLike("50%_\\"), "50\\%\\_\\\\");
  assert.match(queries.rows.text, /m.model_key\s+LIMIT/);
  assert.deepEqual(queries.rows.values.slice(-2), [25, 0]);
});
test("unknown parameters stay distinct from a model that is too large", () => {
  assert.equal(compatibility(null).label, "Unknown");
  assert.equal(compatibility("does-not-fit").label, "Too large");
  assert.equal(compatibility("4-bit").label, "Needs INT4");
  assert.equal(compact(null), "Unknown");
  assert.equal(compact(0), "0");
});
