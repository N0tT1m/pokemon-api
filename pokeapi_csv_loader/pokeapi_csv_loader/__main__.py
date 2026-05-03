"""Entrypoint: ensure schema, then run all loaders against DATABASE_URI."""
from __future__ import annotations

import os
import sys

import psycopg2

from .loaders import (
    load_ability_names,
    load_item_attributes_and_extra,
    load_item_names,
    load_move_meta,
    load_move_names,
    load_moves_canonical,
    load_past_abilities,
    load_past_types,
    load_pokemon_moves_vg,
    load_type_names,
)
from .schema import SCHEMA_SQL


def main() -> int:
    db_uri = os.environ.get("DATABASE_URI")
    if not db_uri:
        print("DATABASE_URI not set", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_uri)
    conn.set_client_encoding("UTF8")
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            conn.commit()

            print("Loading canonical moves...", flush=True)
            n = load_moves_canonical(cur)
            conn.commit()
            print(f"  {n} moves_canonical rows", flush=True)

            print("Loading move meta + stat changes...", flush=True)
            n = load_move_meta(cur)
            conn.commit()
            print(f"  {n} move_meta rows", flush=True)

            print("Loading past types...", flush=True)
            n = load_past_types(cur)
            conn.commit()
            print(f"  {n} past_types rows", flush=True)

            print("Loading past abilities...", flush=True)
            n = load_past_abilities(cur)
            conn.commit()
            print(f"  {n} past_abilities rows", flush=True)

            for label, fn in (
                ("item names", load_item_names),
                ("move names", load_move_names),
                ("ability names", load_ability_names),
                ("type names", load_type_names),
            ):
                print(f"Loading {label}...", flush=True)
                n = fn(cur)
                conn.commit()
                print(f"  {n} rows", flush=True)

            print("Loading item attributes + extras...", flush=True)
            n_attr, n_extra = load_item_attributes_and_extra(cur)
            conn.commit()
            print(f"  {n_attr} attribute rows, {n_extra} extra rows", flush=True)

            print("Loading per-version-group learnset (large)...", flush=True)
            n = load_pokemon_moves_vg(cur)
            conn.commit()
            print(f"  {n} pokemon_moves_vg rows", flush=True)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
