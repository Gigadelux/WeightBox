"""The single database gateway for the ETL. Each phase is handed one
PostgresConnector; no other module opens a connection.

Two clients on the same database: a psycopg 3 connection for DDL, parameterised
SQL, COPY bulk load and information_schema inspection, and a SQLAlchemy Core
engine used only as the pandas read/write bridge.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterator, Sequence
from typing import Any

import pandas as pd
import psycopg
from psycopg import sql as pgsql
from psycopg.rows import dict_row
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from services.config import Settings

log = logging.getLogger("weightbox.etl.postgres")


class PostgresConnector:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._conn: psycopg.Connection | None = None
        self._engine: Engine | None = None

    # lifecycle

    @property
    def conn(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            log.debug("opening psycopg connection")
            self._conn = psycopg.connect(self._settings.pg_dsn, autocommit=False)
        return self._conn

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self._settings.sqlalchemy_url,
                pool_pre_ping=True,
                future=True,
            )
        return self._engine

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        if self._engine is not None:
            self._engine.dispose()
        self._conn = None
        self._engine = None

    def __enter__(self) -> "PostgresConnector":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        """Commit on success, roll back on any exception."""
        conn = self.conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # statement execution

    def execute(self, query: str, params: Sequence[Any] | dict[str, Any] | None = None) -> int:
        """Run one statement inside a transaction; return affected row count."""
        with self.transaction() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

    def execute_script(self, script: str) -> None:
        """Run a multi-statement SQL script (DDL). One transaction."""
        with self.transaction() as conn, conn.cursor() as cur:
            cur.execute(script)

    def execute_many(self, query: str, rows: Sequence[Sequence[Any]]) -> None:
        with self.transaction() as conn, conn.cursor() as cur:
            cur.executemany(query, rows)

    def fetch_all(
        self, query: str, params: Sequence[Any] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def fetch_one(
        self, query: str, params: Sequence[Any] | dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetch_scalar(
        self, query: str, params: Sequence[Any] | dict[str, Any] | None = None
    ) -> Any:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row else None

    # pandas bridge

    def read_df(
        self, query: str, params: Sequence[Any] | dict[str, Any] | None = None
    ) -> pd.DataFrame:
        with self.engine.connect() as sa_conn:
            return pd.read_sql(query, sa_conn, params=params)

    def copy_df(
        self,
        df: pd.DataFrame,
        *,
        schema: str,
        table: str,
        columns: Sequence[str] | None = None,
    ) -> int:
        """Bulk-load a DataFrame with ``COPY ... FROM STDIN``.

        ``NaN``/``NaT``/``None`` become SQL ``NULL``. Column order follows
        ``columns`` (default: the DataFrame's own order).
        """
        cols = list(columns) if columns is not None else list(df.columns)
        target = pgsql.SQL("{}.{} ({})").format(
            pgsql.Identifier(schema),
            pgsql.Identifier(table),
            pgsql.SQL(", ").join(pgsql.Identifier(c) for c in cols),
        )
        copy_stmt = pgsql.SQL("COPY {} FROM STDIN").format(target)
        frame = df[cols].astype(object).where(df[cols].notna(), None)
        n = 0
        with self.transaction() as conn, conn.cursor() as cur:
            with cur.copy(copy_stmt) as copy:
                for record in frame.itertuples(index=False, name=None):
                    copy.write_row(tuple(_adapt(v) for v in record))
                    n += 1
        return n

    # introspection

    def table_exists(self, schema: str, name: str) -> bool:
        return bool(
            self.fetch_scalar(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
                """,
                (schema, name),
            )
        )

    def relation_exists(self, schema: str, name: str) -> bool:
        """True for tables *or* materialized views."""
        return bool(
            self.fetch_scalar(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s AND c.relname = %s
                      AND c.relkind IN ('r', 'm', 'p')
                )
                """,
                (schema, name),
            )
        )

    def columns(self, schema: str, name: str) -> dict[str, dict[str, Any]]:
        rows = self.fetch_all(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, name),
        )
        return {
            r["column_name"]: {
                "data_type": r["data_type"],
                "nullable": r["is_nullable"] == "YES",
            }
            for r in rows
        }

    def index_exists(self, name: str) -> bool:
        return bool(
            self.fetch_scalar(
                "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = %s)",
                (name,),
            )
        )

    def row_count(self, schema: str, name: str) -> int:
        return int(
            self.fetch_scalar(
                pgsql.SQL("SELECT count(*) FROM {}.{}").format(
                    pgsql.Identifier(schema), pgsql.Identifier(name)
                )
            )
        )


def _adapt(value: Any) -> Any:
    """NULL for missing values; whole-number floats become ints so COPY can feed
    smallint/integer columns."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
        if isinstance(value, float) and value.is_integer():
            return int(value)
    return value
