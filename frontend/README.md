# WeightBox frontend

Next.js 16 + React 19 + Tailwind CSS 4. Docker uses Node 22 and Next.js standalone
output. The hardware workbench queries PostgreSQL directly from server code;
Python owns the ETL. There is no separate API service.

- `/`: GPU selection, model search, compatibility filters, pagination, model
  details, and three warehouse comparisons.
- `/methodology`: memory formulas, quantization assumptions, throughput limits,
  aggregation rules, and project context.
- `/data`: live record counts, source loads, data quality flags, and validation.
- `/api/health`: operational readiness, including the real warehouse.

## Run everything with Docker

From the repository root, follow [the setup instructions](../README.md#quick-start).
After creating the root `.env`, run `sh scripts/start.sh`.
No local Python, Node.js, or PostgreSQL installation is needed.

## Develop inside Docker

After loading the warehouse, run from the repository root:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d --wait frontend
docker compose exec frontend npm run lint
docker compose exec frontend npm test
docker compose exec frontend npm run test:integration
docker compose exec frontend npm run test:http
```

Edits in `src/` and `public/` are mounted read-only and reload automatically.
Linux dependencies and build output stay in the container. Rebuild after
changing packages or configuration files. To return to production:

```bash
docker compose up --build -d --wait frontend
```

## Develop with local Node.js

Use Node 22. Start and populate the database using the root README, then
stop the Docker frontend to free port 3000: `docker compose stop frontend`.
From this directory:

```bash
cp -n .env.example .env.local
# Match POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB to the root .env.
# POSTGRES_HOST=localhost; POSTGRES_PORT must match root POSTGRES_HOST_PORT.
npm ci
npm run dev
```

Open <http://localhost:3000>. The `src/lib/db.js` pool is server-only and uses
the `POSTGRES_*` connection parts. Inside Compose the host is `db`; on the host
it is `localhost`. Do not expose credentials through `NEXT_PUBLIC_*` or client
props. The root `.env` is not automatically loaded by a local Next.js process.

The pool uses a read-only session default. This is an application safeguard,
not a dedicated database role or a permission boundary.

## Production and readiness

`npm run build` produces `.next/standalone`. Docker copies that server, its
traced dependencies, `public/`, and `.next/static/` into a non-root runtime image
and starts `node server.js`. `npm start` remains available for a normal local
Next.js production build.

`GET /api/health` returns 200 only when PostgreSQL is reachable, the dimensions,
fact and three materialized views are populated, and all six validator rows
pass. Otherwise it returns a generic 503 without database error details.
This is an operational readiness endpoint, not a separate API service.

## Data flow and verification

`src/lib/warehouse.js` is server-only and uses the bounded pool in `src/lib/db.js`.
`src/lib/sql.mjs` contains parameterized, read-only queries; `filters.mjs` validates
URL state and allowlists sort orders. Browser requests navigate Next.js pages;
only the Next.js container connects to `db:5432`. No public database URL or
database credential is needed by the browser.

The timeline derives rates from known pairs (`n_headroom`), and domain
accessibility counts distinct known models. The VRAM comparison queries the star
schema directly because the generation materialized view groups by parameter
bucket rather than VRAM. These scopes are described in the interface.

Run the commands above in the development container. Unit tests cover URL
validation and query construction. Integration tests require the loaded real
warehouse and fail if credentials or the database are unavailable; they do not
silently skip. They compare filters and all three analyses against independent
queries over the facts, including unknown values and stable pagination. HTTP
checks cover the supplied dataset's page states and scan served browser assets
for the configured database password. They require a running frontend.

To run the HTTP checks against the standalone production container without
installing test dependencies, run from the repository root:

```bash
docker compose exec -T frontend node --input-type=module < frontend/src/lib/tests/http.test.mjs
```

Production images omit development dependencies. To run lint and tests, use the
development Compose override; return to production with the command above.
Production builds do not require a database connection. Pages query at request
time and show a recoverable unavailable state when the warehouse cannot be read.
