"""Build-time CSV download.

Run during the Docker image build to snapshot the PokeAPI CSVs we need into
/app/csv_data/. At runtime csv_fetch.py reads from disk first, falls back to
HTTP only when a file is missing (useful in dev).
"""
from __future__ import annotations

import os
import sys
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"

# Every CSV referenced by any loader. Keep this list in sync with loaders.py.
CSVS = [
    # canonical entity tables
    "pokemon",
    "pokemon_species",
    "moves",
    "items",
    "abilities",
    "types",
    "languages",
    "version_groups",
    "generations",
    "stats",
    # move metadata
    "move_meta",
    "move_meta_ailments",
    "move_meta_categories",
    "move_meta_stat_changes",
    "move_damage_classes",
    "move_targets",
    # past types/abilities
    "pokemon_types_past",
    "pokemon_abilities_past",
    # localized names
    "item_names",
    "move_names",
    "ability_names",
    "type_names",
    # item attributes + fling + baby trigger
    "item_attributes",
    "item_attributes_map",
    "item_fling_effects",
    "evolution_chains",
    # learnset
    "pokemon_moves",
    "pokemon_move_methods",
]


def main() -> int:
    out_dir = os.environ.get("CSV_DATA_DIR", "/app/csv_data")
    os.makedirs(out_dir, exist_ok=True)
    for name in CSVS:
        url = f"{BASE_URL}/{name}.csv"
        target = os.path.join(out_dir, f"{name}.csv")
        print(f"  {name}.csv", flush=True)
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
        with open(target, "wb") as f:
            f.write(data)
    print(f"Snapshotted {len(CSVS)} CSVs into {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
