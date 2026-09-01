#!/usr/bin/env python3
"""Export the scraped tables from a live Postgres deployment into pokedex.db.

This is an alternative to re-running the 25 spiders. The Postgres database the
Postgres deployment already serves holds exactly the same scraped tables, so
copying them is both far faster than a fresh scrape and guarantees the Azure
image serves byte-identical data to the Postgres app.

    python3 pg_export.py --dsn postgresql://pokedex:pokedex@host:5432/pokedex

It only covers the *scraped* tables. The PokeAPI CSV tables (move_names,
pokemon_moves_vg, moves_canonical, ...) are not present in the Postgres
deployment and still come from csv_loader.py — build_db.py --from-postgres
runs both halves in the right order.

The Postgres side is opened read-only (a READ ONLY transaction on top of
default_transaction_read_only), so pointing this at production is safe.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Iterator

import writer
from schema import TABLES

DEFAULT_DSN = os.environ.get(
    "POKEDEX_PG_DSN", "postgresql://pokedex:pokedex@localhost:5432/pokedex"
)

# Rows per fetch/executemany batch. Large enough to keep the round-trip count
# low on the 17k-row tables, small enough that `moves` (34MB) never lands in
# memory all at once.
BATCH = 2000


def _encode_value(value: Any) -> Any:
    """Normalise a psycopg value that writer.encode_row does not cover.

    Only timestamps need it: raid_events.scraped_at is the single TIMESTAMPTZ
    column, and the SQLite schema stores it as ISO-8601 UTC text so that
    db.UTCTimestamp()'s strftime can read it back.
    """
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def _pg_tables(cur) -> set[str]:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    return {r[0] for r in cur.fetchall()}


def _columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({writer._quote(table)})")]


def _batches(cur, size: int) -> Iterator[list[tuple]]:
    while True:
        rows = cur.fetchmany(size)
        if not rows:
            return
        yield rows


def export_table(pg_conn, conn: sqlite3.Connection, table: str) -> int:
    """Copy one table. Returns the row count written."""
    with pg_conn.cursor() as cur:
        pg_cols = _columns(cur, table)
        sq_cols = set(_sqlite_columns(conn, table))

        # Only copy columns both sides agree on. A column present in Postgres
        # but not in the SQLite schema is a real mismatch worth failing on
        # rather than silently dropping.
        missing = [c for c in pg_cols if c not in sq_cols]
        if missing:
            raise SystemExit(
                f"!!! {table}: columns exist in Postgres but not in the SQLite "
                f"schema: {missing}. schema.py is out of date."
            )

        quoted = ", ".join(writer._quote(c) for c in pg_cols)
        # Server-side cursor: stream rather than materialise 600k rows.
        with pg_conn.cursor(name=f"export_{table}") as stream:
            stream.itersize = BATCH
            stream.execute(f"SELECT {quoted} FROM {writer._quote(table)}")

            placeholders = ", ".join(f":{c}" for c in pg_cols)
            sql = (
                f"INSERT OR REPLACE INTO {writer._quote(table)} "
                f"({', '.join(writer._quote(c) for c in pg_cols)}) "
                f"VALUES ({placeholders})"
            )

            total = 0
            for rows in _batches(stream, BATCH):
                encoded = []
                for row in rows:
                    raw = {c: _encode_value(v) for c, v in zip(pg_cols, row)}
                    encoded.append(writer.encode_row(table, raw))
                conn.executemany(sql, encoded)
                total += len(rows)
            conn.commit()
            return total


def export_all(dsn: str, conn: sqlite3.Connection) -> dict[str, int]:
    try:
        import psycopg
    except ImportError:
        raise SystemExit(
            "psycopg is required for --from-postgres. Install it with:\n"
            "    pip install 'psycopg[binary]'"
        )

    counts: dict[str, int] = {}
    # autocommit=False plus a read-only transaction: nothing this script does
    # can write to the source database.
    with psycopg.connect(dsn, connect_timeout=15) as pg_conn:
        pg_conn.read_only = True
        with pg_conn.cursor() as cur:
            present = _pg_tables(cur)

        exportable = [t for t in TABLES if t in present]
        skipped = [t for t in TABLES if t not in present]

        print(f"Postgres has {len(present)} tables; "
              f"exporting {len(exportable)} that the SQLite schema defines")
        if skipped:
            print(f"  not in Postgres, left to csv_loader: {len(skipped)} tables")

        for table in exportable:
            n = export_table(pg_conn, conn, table)
            counts[table] = n
            print(f"  {table:<28} {n:>8,} rows", flush=True)

    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dsn", default=DEFAULT_DSN,
                    help="Postgres connection string (default: $POKEDEX_PG_DSN)")
    ap.add_argument("--db-path", default=writer.DEFAULT_DB_PATH,
                    help="output SQLite file (default: pokedex.db)")
    ap.add_argument("--fresh", action="store_true",
                    help="delete the SQLite file first")
    args = ap.parse_args()

    conn = writer.open_db(args.db_path, fresh=args.fresh)
    writer.apply_schema(conn)
    counts = export_all(args.dsn, conn)
    writer.finalize(conn)

    total = sum(counts.values())
    print(f"\nExported {total:,} rows across {len(counts)} tables into {args.db_path}")
    empty = [t for t, n in counts.items() if n == 0]
    if empty:
        print(f"WARNING: {len(empty)} exported table(s) were empty in Postgres: "
              f"{', '.join(sorted(empty))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
