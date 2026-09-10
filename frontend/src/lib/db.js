import "server-only";
import pg from "pg";

// This module is imported only by server code. No credentials enter client props.
export function getPool() {
  if (!globalThis.weightboxPool) {
    globalThis.weightboxPool = new pg.Pool({
      host: process.env.POSTGRES_HOST || "localhost",
      port: Number(process.env.POSTGRES_PORT || 5432),
      user: process.env.POSTGRES_USER,
      password: process.env.POSTGRES_PASSWORD,
      database: process.env.POSTGRES_DB,
      max: 5,
      connectionTimeoutMillis: 3000,
      idleTimeoutMillis: 30000,
      statement_timeout: 5000,
      options: "-c default_transaction_read_only=on",
    });
    globalThis.weightboxPool.on("error", () => {
      console.error("WeightBox: an idle database connection failed");
    });
  }
  return globalThis.weightboxPool;
}
