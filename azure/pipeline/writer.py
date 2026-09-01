"""Reusable SQLite writer for the Azure ingest pipeline.

Responsibilities:
  * open the database and apply load-time pragmas (WAL, synchronous=NORMAL)
  * apply schema.SCHEMA_SQL
  * JSON-encode Python lists for the TEXT-holding-a-JSON-array columns
  * provide upsert helpers that mirror the ON CONFLICT behaviour of the
    Postgres pipelines
  * compact the shipped file at the end (VACUUM + ANALYZE)

The upsert helpers deliberately mirror the four distinct conflict behaviours
the Postgres sources use:

  Postgres                                  ->  helper argument
  ------------------------------------------------------------------
  SET c = EXCLUDED.c                        ->  update=[...]
  SET c = COALESCE(EXCLUDED.c, table.c)     ->  coalesce=[...]
  SET c = EXCLUDED.c OR table.c   (boolean) ->  or_merge=[...]
  DO NOTHING                                ->  do_nothing=True

Boolean OR-merge becomes MAX(excluded.c, table.c) because booleans are stored
as 0/1 integers.
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Iterable, Mapping, Sequence

from schema import ARRAY_COLUMNS, BOOLEAN_COLUMNS, SCHEMA_SQL, TABLES

DEFAULT_DB_PATH = os.environ.get("POKEDEX_DB_PATH", "pokedex.db")


# ---------------------------------------------------------------------------
# Value encoding
# ---------------------------------------------------------------------------

def json_array(value: Any) -> str:
    """Encode a value destined for a TEXT-holding-JSON-array column.

    Guarantees a valid JSON array string, never NULL and never Postgres
    '{a,b}' literal syntax. None / empty / missing all become '[]' so the Go
    read side can json_each() or json.Unmarshal() unconditionally.
    """
    if value is None:
        return "[]"
    if isinstance(value, str):
        # Already-encoded JSON passes through; a bare string becomes a
        # one-element array. A Postgres '{a,b}' literal is rejected loudly
        # rather than silently shipped.
        stripped = value.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            raise ValueError(
                f"refusing to store Postgres array literal as JSON: {value!r}"
            )
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                decoded = json.loads(stripped)
            except json.JSONDecodeError:
                return json.dumps([value], ensure_ascii=False)
            if isinstance(decoded, list):
                return json.dumps(decoded, ensure_ascii=False)
        return json.dumps([value], ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return json.dumps([str(v) for v in value], ensure_ascii=False)
    return json.dumps([str(value)], ensure_ascii=False)


def _to_bool_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("1", "t", "true", "yes", "y") else 0
    return 1 if value else 0


def encode_row(table: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalise a row dict for `table`: JSON arrays and 0/1 booleans."""
    arrays = ARRAY_COLUMNS.get(table, frozenset())
    booleans = BOOLEAN_COLUMNS.get(table, frozenset())
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key in arrays:
            out[key] = json_array(value)
        elif key in booleans:
            out[key] = _to_bool_int(value)
        else:
            out[key] = value
    # An array column that the item omitted entirely still needs '[]' rather
    # than falling back to a NULL.
    for col in arrays:
        out.setdefault(col, "[]")
    return out


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp, e.g. '2026-07-18T12:34:56Z'.

    Matches the format db/queries.go reads back with strftime.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quote(identifier: str) -> str:
    """Quote a bare column name; pass expressions (which contain non-word
    characters) through untouched so conflict targets like
    COALESCE(evolves_from, '') still work."""
    if identifier.replace("_", "").isalnum():
        return f'"{identifier}"'
    return identifier


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def open_db(path: str = DEFAULT_DB_PATH, *, fresh: bool = False) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite database with load-time pragmas."""
    if fresh:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(path + suffix)
            except FileNotFoundError:
                pass
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")  # ~64MB page cache during load
    # Left OFF during load so ingest order does not matter, matching the
    # commit-per-item behaviour of the Postgres pipelines.
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def verify_tables(conn: sqlite3.Connection) -> list[str]:
    """Return the list of missing tables (empty when the schema is complete)."""
    live = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }
    return sorted(set(TABLES) - live)


def finalize(conn: sqlite3.Connection) -> None:
    """Compact and analyse the finished database, then restore safe pragmas.

    Call once at the very end of the build so the shipped file is small and
    the query planner has statistics.
    """
    conn.commit()
    conn.execute("PRAGMA optimize")
    conn.execute("ANALYZE")
    conn.commit()
    # VACUUM cannot run inside a transaction; also fold the WAL back into the
    # main file so a single pokedex.db is all that needs shipping.
    conn.isolation_level = None
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("VACUUM")
    conn.execute("PRAGMA synchronous=FULL")
    conn.isolation_level = ""


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def insert(conn: sqlite3.Connection, table: str, row: Mapping[str, Any]) -> None:
    """Plain INSERT, mirroring the Postgres pipelines' unconstrained inserts
    (the `moves` and `locations` tables)."""
    data = encode_row(table, row)
    cols = list(data)
    sql = (
        f"INSERT INTO {table} ({', '.join(_quote(c) for c in cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)})"
    )
    conn.execute(sql, data)


def upsert(
    conn: sqlite3.Connection,
    table: str,
    row: Mapping[str, Any],
    *,
    conflict: Sequence[str],
    update: Sequence[str] = (),
    coalesce: Sequence[str] = (),
    or_merge: Sequence[str] = (),
    set_raw: Mapping[str, str] | None = None,
    do_nothing: bool = False,
) -> None:
    """INSERT ... ON CONFLICT(...) DO UPDATE / DO NOTHING.

    `conflict` entries may be bare column names or expressions matching an
    expression index (e.g. "COALESCE(tera_type, '')").
    `set_raw` maps a column to a raw SQL assignment expression, for the few
    cases (array union, scraped_at refresh) that need it.
    """
    data = encode_row(table, row)
    cols = list(data)
    target = ", ".join(_quote(c) for c in conflict)
    sql = (
        f"INSERT INTO {table} ({', '.join(_quote(c) for c in cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)}) "
        f"ON CONFLICT ({target}) "
    )

    if do_nothing:
        conn.execute(sql + "DO NOTHING", data)
        return

    assignments: list[str] = []
    for col in update:
        assignments.append(f"{_quote(col)} = excluded.{_quote(col)}")
    for col in coalesce:
        assignments.append(
            f"{_quote(col)} = COALESCE(excluded.{_quote(col)}, {table}.{_quote(col)})"
        )
    for col in or_merge:
        # Postgres: EXCLUDED.c OR table.c  — booleans are 0/1 integers here.
        assignments.append(
            f"{_quote(col)} = MAX(excluded.{_quote(col)}, {table}.{_quote(col)})"
        )
    for col, expr in (set_raw or {}).items():
        assignments.append(f"{_quote(col)} = {expr}")

    if not assignments:
        conn.execute(sql + "DO NOTHING", data)
        return

    conn.execute(sql + "DO UPDATE SET " + ", ".join(assignments), data)


def json_array_union(table: str, column: str) -> str:
    """Raw SET expression that unions the incoming JSON array into the stored
    one, deduplicated and sorted.

    Mirrors the Postgres location_encounters upsert:
        ARRAY(SELECT DISTINCT unnest FROM unnest(t.games || EXCLUDED.games) ORDER BY 1)
    """
    return (
        "(SELECT json_group_array(v) FROM ("
        f"  SELECT DISTINCT value AS v FROM json_each({table}.{column})"
        "  UNION "
        f"  SELECT DISTINCT value AS v FROM json_each(excluded.{column})"
        "  ORDER BY v))"
    )


def executemany_upsert(
    conn: sqlite3.Connection,
    table: str,
    rows: Iterable[Mapping[str, Any]],
    **kwargs: Any,
) -> int:
    """Bulk convenience wrapper. Returns the number of rows processed."""
    count = 0
    for row in rows:
        upsert(conn, table, row, **kwargs)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

# Gen 6+ type chart. Only non-1.0 multipliers are stored; missing rows = 1.0.
# Copied verbatim from pokemondb_scraper/pokemondb_scraper/pipelines.py so this
# pipeline has no import dependency on the Postgres one.
TYPE_MATCHUPS = {
    "normal":   {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
    "poison":   {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground":   {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying":   {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon":   {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark":     {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "fairy":    {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}


def seed_type_matchups(conn: sqlite3.Connection) -> int:
    """Populate the static type chart. Idempotent."""
    rows = [
        (atk, dfn, mult)
        for atk, defs in TYPE_MATCHUPS.items()
        for dfn, mult in defs.items()
    ]
    conn.executemany(
        "INSERT INTO type_matchups (attacking_type, defending_type, multiplier) "
        "VALUES (?, ?, ?) ON CONFLICT (attacking_type, defending_type) "
        "DO UPDATE SET multiplier = excluded.multiplier",
        rows,
    )
    conn.commit()
    return len(rows)
