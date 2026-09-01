# Azure ingest pipeline (SQLite)

Builds `pokedex.db`, a single self-contained SQLite file holding the same 52
tables the Postgres deployment uses. This is a **parallel** ingest path — the
Postgres scrapers in `pokemondb_scraper/` and `pokeapi_csv_loader/` are
untouched and keep working exactly as before. Both paths drive the same
spiders; only the item pipeline differs.

## Layout

| File | Purpose |
| --- | --- |
| `schema.py` | All 52 tables as SQLite DDL, plus `TABLES`, `ARRAY_COLUMNS`, `BOOLEAN_COLUMNS` |
| `writer.py` | Connection lifecycle, pragmas, JSON-array encoding, upsert helpers, `VACUUM`/`ANALYZE` |
| `pipelines.py` | `SQLitePipeline` — Scrapy item pipeline, mirrors `PostgresPipeline` |
| `csv_loader.py` | PokeAPI CSV load path (the `pokeapi_csv_loader` equivalent) |
| `build_db.py` | Single entrypoint: schema → spiders → CSVs → compact |

## Producing `pokedex.db`

```sh
pip install -r requirements.txt

# Optional but recommended for reproducible/offline builds: snapshot the
# PokeAPI CSVs once (~28 files).
python3 build_db.py --prefetch --csv-dir ./csv_data

# Full build.
python3 build_db.py --db-path ./pokedex.db --csv-dir ./csv_data --fresh
```

That single command creates the file, applies the schema, runs all 25 spiders,
loads the PokeAPI CSVs, and finishes with `VACUUM` + `ANALYZE`. It prints a
per-table row count summary and warns about any table that ended up empty.

Useful flags while iterating:

```sh
python3 build_db.py --skip-scrape                  # CSV data only (fast)
python3 build_db.py --skip-csv                     # scraped data only
python3 build_db.py --only pokemondb_pokemon       # one spider
python3 build_db.py --keep-going                   # don't abort on a spider failure
```

### Docker

```dockerfile
COPY azure/pipeline /app/azure/pipeline
COPY pokemondb_scraper /app/pokemondb_scraper
RUN pip install -r /app/azure/pipeline/requirements.txt
RUN python3 /app/azure/pipeline/build_db.py --prefetch --csv-dir /app/csv_data
RUN python3 /app/azure/pipeline/build_db.py \
        --db-path /app/pokedex.db --csv-dir /app/csv_data --fresh
```

## Known upstream gap: `item_attributes`

PokeAPI has **removed** `item_attributes.csv` and `item_attributes_map.csv`
from its CSV dump — both now 404. `csv_loader.py` treats them as optional and
logs a note instead of failing, so `item_attributes` builds empty and
`db/queries.go:GetItemAttributes` will return no rows. `item_extra` (fling
power/effect, baby trigger) is unaffected and still loads.

This is pre-existing upstream drift, not a translation artifact: the Postgres
`pokeapi_csv_loader` hits the same 404 on a fresh build, and its
`prefetch.py` still lists both files. Populating the table again means finding
a new source for item attributes.

## Storage conventions

The Go read side depends on these, so they are contractual:

* **Arrays.** Postgres `TEXT[]` columns are `TEXT` holding a **JSON array**,
  e.g. `["Water","Ice"]`. Never Postgres `{a,b}` literal syntax — `writer.json_array()`
  raises if handed one. Never `NULL` where an empty array is meant: the column
  is `NOT NULL DEFAULT '[]'` and the writer fills in `[]` for omitted values,
  so `json_each()` is always safe without a null guard. The array columns are
  enumerated in `schema.ARRAY_COLUMNS`.
* **Timestamps.** `TIMESTAMPTZ` became `TEXT` holding ISO-8601 UTC, e.g.
  `2026-07-18T12:34:56Z`, written by
  `strftime('%Y-%m-%dT%H:%M:%SZ','now')` — readable back with `strftime`.
  Only `raid_events.scraped_at` is affected.
* **Booleans.** `BOOLEAN` became `INTEGER` 0/1. Postgres's
  `SET c = EXCLUDED.c OR table.c` merge becomes `MAX(excluded.c, table.c)`.
  Enumerated in `schema.BOOLEAN_COLUMNS`.
* **Surrogate keys.** `SERIAL` became `INTEGER PRIMARY KEY AUTOINCREMENT`.
* **`raid_counters.rank`** is quoted as `"rank"` everywhere, since `rank` is a
  SQL window-function keyword.

Load-time pragmas are `journal_mode=WAL` and `synchronous=NORMAL`.
`writer.finalize()` checkpoints the WAL, switches back to `journal_mode=DELETE`
and runs `VACUUM` + `ANALYZE`, so the build emits one compact `pokedex.db` with
no sidecar `-wal`/`-shm` files.

Foreign keys are declared but `PRAGMA foreign_keys` is left **off** during load,
so spider run order does not matter — matching the effective behaviour of the
Postgres pipeline, which committed per item.

## Indexes

Every unique constraint and index from the Postgres sources is preserved,
including the `COALESCE(...)`-based expression indexes (SQLite supports these,
and supports naming them as `ON CONFLICT` targets). On top of those,
`LOWER(col)` expression indexes back every case-insensitive lookup in
`db/queries.go` — `LOWER(name)` on `pokemon`, `item_details`, `move_details`,
`ability_details`, `berries`, `z_moves`; `LOWER(pokemon_name)` on the
per-Pokemon tables; `LOWER(game)` on the game-filtered tables; and so on. 72
indexes in total.

## Read-side note

The read side is done: `go build -tags sqlite` compiles `db/queries.go` against
this file with no query edits. The dialect differences the schema is shaped for
are rendered by helpers in `db/dialect_sqlite.go`, and `db/connect_sqlite.go`
rewrites `$N` placeholders to `?N`:

| Postgres | SQLite | Rendered by |
| --- | --- | --- |
| `$1` placeholders | `?` | `rewritePlaceholders` |
| `$1 = ANY(games)` | `EXISTS (SELECT 1 FROM json_each(games) WHERE value = ?)` | `ArrayContains` |
| `UNNEST(types)` / `unnest(games)` | `json_each(...)` | `ArrayDistinct` / `ArrayContainsFold` |
| `to_char(scraped_at AT TIME ZONE 'UTC', ...)` | `strftime('%Y-%m-%dT%H:%M:%SZ', ...)` | `UTCTimestamp` |
| `ILIKE` | `LOWER(col) LIKE LOWER(?)` | `LikeFold` |
| `year::TEXT` | `CAST(year AS TEXT)` | `CastText` |

`ORDER BY x NULLS LAST` needs no rewrite — SQLite has supported it since 3.30,
and the shipped `modernc.org/sqlite` is 3.53. Likewise `is_active = TRUE` works
against the 0/1 INTEGER columns (`TRUE` is a keyword since 3.23).

No table or column renames are needed — the names match one-for-one.

See `azure/README.md` for how the two builds are wired and deployed.
