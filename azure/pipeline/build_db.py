#!/usr/bin/env python3
"""Single entrypoint that builds pokedex.db end to end.

    python3 build_db.py --db-path pokedex.db

Runs, in order:
  1. create the SQLite file and apply the 52-table schema
  2. seed the static type chart
  3. run every pokemondb/bulbapedia/game8 spider, writing through
     pipelines.SQLitePipeline
  4. run the PokeAPI CSV loaders
  5. VACUUM + ANALYZE so the shipped file is compact

The spiders are the existing ones in pokemondb_scraper/ — this script only
overrides ITEM_PIPELINES so they write to SQLite instead of Postgres. Nothing
under pokemondb_scraper/ or pokeapi_csv_loader/ is modified.

Docker builds can call this as one command. Use --prefetch to snapshot the
PokeAPI CSVs into the image first, then --offline at build time.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import csv_loader
import writer
from schema import TABLES

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRAPER_DIR = os.path.join(REPO_ROOT, "pokemondb_scraper")

# Spider run order, mirroring pokemondb_scraper/entrypoint.sh. Pokemon must go
# first: several later tables reference pokemon(name).
SPIDERS = [
    "pokemondb_pokemon",
    "pokemondb_egg_moves",
    "pokemondb_regional_dex",
    "pokemondb_locations",
    "pokemondb_abilities",
    "pokemondb_items",
    "pokemondb_moves",
    "pokemondb_natures",
    "bulbapedia_item_locations",
    "bulbapedia_tm_locations",
    "bulbapedia_pokemon",
    "bulbapedia_pokemon_locations",
    "pokemondb_berries",
    "pokemondb_trainers",
    "pokemondb_zmoves",
    "pokemondb_go",
    "pokemondb_contest",
    "pokemondb_battle_facilities",
    "bulbapedia_classification",
    "bulbapedia_ingame_trades",
    "bulbapedia_events",
    "bulbapedia_outbreaks",
    "bulbapedia_version_exclusives",
    "bulbapedia_move_tutors",
    "game8_raids",
]


def run_spiders(db_path: str, spiders: list[str], keep_going: bool) -> list[str]:
    """Run each spider with the SQLite pipeline. Returns the failed spiders."""
    env = dict(os.environ)
    # Make schema/writer/pipelines importable from inside the Scrapy process.
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")
    env["POKEDEX_DB_PATH"] = os.path.abspath(db_path)

    failed: list[str] = []
    for spider in spiders:
        print(f"=== Running {spider} ===", flush=True)
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "--nolog", "-L", "WARNING",
            # JSON, not a Python dict literal: Scrapy 2.13+ parses dict-valued
            # -s settings with json.loads, which rejects single quotes.
            "-s", 'ITEM_PIPELINES={"pipelines.SQLitePipeline": 300}',
            "-s", f"POKEDEX_DB_PATH={os.path.abspath(db_path)}",
        ]
        proc = subprocess.run(cmd, cwd=SCRAPER_DIR, env=env)
        if proc.returncode != 0:
            failed.append(spider)
            msg = f"!!! spider {spider} exited {proc.returncode}"
            if not keep_going:
                raise SystemExit(msg)
            print(msg, flush=True)
    return failed


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pokedex.db end to end.")
    ap.add_argument("--db-path", default=os.environ.get("POKEDEX_DB_PATH", "pokedex.db"),
                    help="output SQLite file (default: pokedex.db)")
    ap.add_argument("--csv-dir", default=None,
                    help="directory holding the PokeAPI CSV snapshot "
                         "(default: $CSV_DATA_DIR or ./csv_data)")
    ap.add_argument("--prefetch", action="store_true",
                    help="download the PokeAPI CSVs to --csv-dir and exit")
    ap.add_argument("--skip-scrape", action="store_true",
                    help="skip the Scrapy spiders (CSV data only)")
    ap.add_argument("--skip-csv", action="store_true",
                    help="skip the PokeAPI CSV loaders (scraped data only)")
    ap.add_argument("--only", nargs="*", metavar="SPIDER",
                    help="run only these spiders")
    ap.add_argument("--keep-going", action="store_true",
                    help="continue when an individual spider fails")
    ap.add_argument("--fresh", action="store_true",
                    help="delete any existing database file first")
    args = ap.parse_args()

    if args.csv_dir:
        csv_loader.LOCAL_DIR = args.csv_dir
        os.environ["CSV_DATA_DIR"] = args.csv_dir

    if args.prefetch:
        csv_loader.prefetch(args.csv_dir)
        return 0

    started = time.time()
    db_path = os.path.abspath(args.db_path)
    print(f"=== Building {db_path} ===", flush=True)

    conn = writer.open_db(db_path, fresh=args.fresh)
    writer.apply_schema(conn)

    missing = writer.verify_tables(conn)
    if missing:
        print(f"!!! schema incomplete, missing: {missing}", file=sys.stderr)
        return 1
    print(f"Schema applied: {len(TABLES)} tables", flush=True)

    n = writer.seed_type_matchups(conn)
    print(f"Seeded {n} type matchup rows", flush=True)

    # The spiders run in their own processes and open their own connections,
    # so close ours for the duration to avoid holding a write lock.
    conn.commit()
    conn.close()

    failed: list[str] = []
    if args.skip_scrape:
        print("Skipping spiders (--skip-scrape)", flush=True)
    else:
        failed = run_spiders(db_path, args.only or SPIDERS, args.keep_going)

    conn = writer.open_db(db_path)

    if args.skip_csv:
        print("Skipping PokeAPI CSV loaders (--skip-csv)", flush=True)
    else:
        print("=== Loading PokeAPI CSV data ===", flush=True)
        csv_loader.run_all(conn)

    print("=== Compacting ===", flush=True)
    writer.finalize(conn)

    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES
    }
    conn.close()

    empty = [t for t, c in counts.items() if c == 0]
    total = sum(counts.values())
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    elapsed = time.time() - started

    print(f"=== Done in {elapsed:.0f}s ===", flush=True)
    print(f"{db_path}  {size_mb:.1f} MB  {total} rows across {len(TABLES)} tables")
    if empty:
        print(f"WARNING: {len(empty)} table(s) empty: {', '.join(sorted(empty))}")
    if failed:
        print(f"WARNING: {len(failed)} spider(s) failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
