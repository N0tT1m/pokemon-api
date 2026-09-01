"""PokeAPI CSV load path, writing to SQLite.

Mirrors pokeapi_csv_loader/pokeapi_csv_loader/{csv_fetch,loaders,__main__}.py
but targets a SQLite file through writer.py. The Postgres loader is untouched.

Differences forced by the target engine:
  * TRUNCATE            -> DELETE FROM
  * COPY ... FROM STDIN -> executemany INSERT (still one transaction)
  * execute_values      -> executemany

CSVs are read from CSV_DATA_DIR (default ./csv_data) if present, otherwise
downloaded from PokeAPI's GitHub raw URL — same contract as the original, so a
Docker build can snapshot them once with prefetch() and stay offline after.
"""
from __future__ import annotations

import csv
import io
import os
import sqlite3
import urllib.request
from typing import Iterable

BASE_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"
LOCAL_DIR = os.environ.get("CSV_DATA_DIR", "csv_data")

# Every CSV referenced by any loader below. Kept in sync with the loaders in
# this module (same list as pokeapi_csv_loader/prefetch.py).
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

#: CSVs that PokeAPI no longer publishes. Their absence degrades one table
#: (item_attributes) rather than failing the build.
OPTIONAL_CSVS = {"item_attributes", "item_attributes_map"}

_CACHE: dict[str, list[dict[str, str]]] = {}


def fetch_csv(name: str) -> list[dict[str, str]]:
    """Fetch a CSV by basename (no extension) and return parsed rows.

    Results are memoised: several loaders read the same entity CSVs and
    re-parsing pokemon_moves.csv (~250k rows) repeatedly is wasteful.
    """
    if name in _CACHE:
        return _CACHE[name]
    local_path = os.path.join(LOCAL_DIR, f"{name}.csv")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        url = f"{BASE_URL}/{name}.csv"
        with urllib.request.urlopen(url, timeout=120) as resp:
            text = resp.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    _CACHE[name] = rows
    return rows


def fetch_csv_optional(name: str) -> list[dict[str, str]]:
    """Like fetch_csv but returns [] when the CSV is absent upstream.

    PokeAPI occasionally drops a CSV from its dump (item_attributes.csv and
    item_attributes_map.csv are gone as of this writing). A removed source
    should degrade one table, not abort the whole build.
    """
    try:
        return fetch_csv(name)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"  note: {name}.csv not available upstream (404) — skipping",
                  flush=True)
            _CACHE[name] = []
            return []
        raise
    except FileNotFoundError:
        return []


def index_by(rows: Iterable[dict], key: str) -> dict[str, dict]:
    """Return {row[key]: row} mapping."""
    return {row[key]: row for row in rows}


def int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def prefetch(out_dir: str | None = None) -> int:
    """Snapshot every CSV in CSVS to disk. Intended for Docker build time."""
    out_dir = out_dir or LOCAL_DIR
    os.makedirs(out_dir, exist_ok=True)
    got = 0
    for name in CSVS:
        url = f"{BASE_URL}/{name}.csv"
        target = os.path.join(out_dir, f"{name}.csv")
        try:
            with urllib.request.urlopen(url, timeout=180) as resp:
                data = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and name in OPTIONAL_CSVS:
                print(f"  {name}.csv — not available upstream (404), skipped",
                      flush=True)
                continue
            raise
        with open(target, "wb") as f:
            f.write(data)
        print(f"  {name}.csv", flush=True)
        got += 1
    print(f"Snapshotted {got}/{len(CSVS)} CSVs into {out_dir}", flush=True)
    return got


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_move_meta(conn: sqlite3.Connection) -> int:
    """Load move_meta + move_stat_changes."""
    moves = index_by(fetch_csv("moves"), "id")
    ailments = {r["id"]: r["identifier"] for r in fetch_csv("move_meta_ailments")}
    categories = {r["id"]: r["identifier"] for r in fetch_csv("move_meta_categories")}
    stats = {r["id"]: r["identifier"] for r in fetch_csv("stats")}

    meta_rows = []
    for r in fetch_csv("move_meta"):
        move = moves.get(r["move_id"])
        if not move:
            continue
        meta_rows.append((
            move["identifier"],
            ailments.get(r["meta_ailment_id"]),
            int_or_none(r.get("ailment_chance")),
            int_or_none(r.get("flinch_chance")),
            int_or_none(r.get("crit_rate")),
            int_or_none(r.get("drain")),
            int_or_none(r.get("healing")),
            int_or_none(r.get("stat_chance")),
            int_or_none(r.get("min_hits")),
            int_or_none(r.get("max_hits")),
            int_or_none(r.get("min_turns")),
            int_or_none(r.get("max_turns")),
            categories.get(r["meta_category_id"]),
        ))

    conn.executemany(
        """
        INSERT INTO move_meta (
            move_identifier, ailment, ailment_chance, flinch_chance,
            crit_rate, drain, healing, stat_chance,
            min_hits, max_hits, min_turns, max_turns, category
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (move_identifier) DO UPDATE SET
            ailment        = excluded.ailment,
            ailment_chance = excluded.ailment_chance,
            flinch_chance  = excluded.flinch_chance,
            crit_rate      = excluded.crit_rate,
            drain          = excluded.drain,
            healing        = excluded.healing,
            stat_chance    = excluded.stat_chance,
            min_hits       = excluded.min_hits,
            max_hits       = excluded.max_hits,
            min_turns      = excluded.min_turns,
            max_turns      = excluded.max_turns,
            category       = excluded.category
        """,
        meta_rows,
    )

    stat_change_rows = []
    for r in fetch_csv("move_meta_stat_changes"):
        move = moves.get(r["move_id"])
        stat = stats.get(r["stat_id"])
        if not move or not stat:
            continue
        stat_change_rows.append((move["identifier"], stat, int(r["change"])))

    if stat_change_rows:
        # Wipe stat_changes for any move we touched, then re-insert — avoids
        # stale rows when PokeAPI revises data.
        touched = sorted({r[0] for r in stat_change_rows})
        conn.executemany(
            "DELETE FROM move_stat_changes WHERE move_identifier = ?",
            [(m,) for m in touched],
        )
        conn.executemany(
            "INSERT INTO move_stat_changes (move_identifier, stat, change) "
            "VALUES (?,?,?) ON CONFLICT (move_identifier, stat) DO UPDATE SET "
            "change = excluded.change",
            stat_change_rows,
        )

    conn.commit()
    return len(meta_rows)


def load_past_types(conn: sqlite3.Connection) -> int:
    """Load pokemon_past_types from PokeAPI's pokemon_types_past CSV."""
    pokemon = index_by(fetch_csv("pokemon"), "id")
    types = {r["id"]: r["identifier"] for r in fetch_csv("types")}
    version_groups = index_by(fetch_csv("version_groups"), "id")
    rows = []
    for r in fetch_csv("pokemon_types_past"):
        poke = pokemon.get(r["pokemon_id"])
        type_ = types.get(r["type_id"])
        vg = version_groups.get(r["generation_id"]) if "generation_id" in r else None
        if not poke or not type_:
            continue
        gen_str = r.get("generation_id") or (vg["generation_id"] if vg else "")
        try:
            gen = int(gen_str)
        except (ValueError, TypeError):
            continue
        rows.append((poke["identifier"], gen, int(r["slot"]), type_))
    if rows:
        conn.executemany(
            "INSERT INTO pokemon_past_types "
            "(pokemon_identifier, generation, slot, type) VALUES (?,?,?,?) "
            "ON CONFLICT (pokemon_identifier, generation, slot) DO UPDATE "
            "SET type = excluded.type",
            rows,
        )
    conn.commit()
    return len(rows)


def load_past_abilities(conn: sqlite3.Connection) -> int:
    """Load pokemon_past_abilities from PokeAPI's pokemon_abilities_past CSV."""
    pokemon = index_by(fetch_csv("pokemon"), "id")
    abilities = {r["id"]: r["identifier"] for r in fetch_csv("abilities")}
    rows = []
    for r in fetch_csv("pokemon_abilities_past"):
        poke = pokemon.get(r["pokemon_id"])
        if not poke:
            continue
        ability = abilities.get(r["ability_id"]) if r["ability_id"] else None
        try:
            gen = int(r["generation_id"])
            slot = int(r["slot"])
        except (ValueError, TypeError):
            continue
        # BOOLEAN -> INTEGER 0/1
        rows.append((poke["identifier"], gen, slot, ability,
                     1 if r["is_hidden"] == "1" else 0))
    if rows:
        conn.executemany(
            "INSERT INTO pokemon_past_abilities "
            "(pokemon_identifier, generation, slot, ability, is_hidden) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT (pokemon_identifier, generation, slot) DO UPDATE "
            "SET ability = excluded.ability, is_hidden = excluded.is_hidden",
            rows,
        )
    conn.commit()
    return len(rows)


_NAMES_PK = {
    "item_names":    "item_identifier",
    "move_names":    "move_identifier",
    "ability_names": "ability_identifier",
    "type_names":    "type_identifier",
}


def _load_localized_names(conn, *, entity_csv: str, names_csv: str,
                          table: str, id_column: str) -> int:
    """Generic loader for the *_names tables."""
    entities = {r["id"]: r["identifier"] for r in fetch_csv(entity_csv)}
    languages = {r["id"]: r["identifier"] for r in fetch_csv("languages")}
    rows = []
    for r in fetch_csv(names_csv):
        ident = entities.get(r[id_column])
        lang = languages.get(r["local_language_id"])
        name = r.get("name", "").strip()
        if not ident or not lang or not name:
            continue
        rows.append((ident, lang, name))
    if not rows:
        return 0
    pk_col = _NAMES_PK[table]
    conn.executemany(
        f"INSERT INTO {table} ({pk_col}, language, localized_name) "
        f"VALUES (?,?,?) "
        f"ON CONFLICT ({pk_col}, language) DO UPDATE SET "
        f"localized_name = excluded.localized_name",
        rows,
    )
    conn.commit()
    return len(rows)


def load_item_names(conn) -> int:
    return _load_localized_names(
        conn, entity_csv="items", names_csv="item_names",
        table="item_names", id_column="item_id",
    )


def load_move_names(conn) -> int:
    return _load_localized_names(
        conn, entity_csv="moves", names_csv="move_names",
        table="move_names", id_column="move_id",
    )


def load_ability_names(conn) -> int:
    return _load_localized_names(
        conn, entity_csv="abilities", names_csv="ability_names",
        table="ability_names", id_column="ability_id",
    )


def load_type_names(conn) -> int:
    return _load_localized_names(
        conn, entity_csv="types", names_csv="type_names",
        table="type_names", id_column="type_id",
    )


def load_item_attributes_and_extra(conn) -> tuple[int, int]:
    """Load item_attributes and item_extra (fling, baby_trigger)."""
    items = index_by(fetch_csv("items"), "id")
    # These two are optional: PokeAPI has dropped them from its CSV dump, so
    # item_attributes may legitimately come back empty. item_extra below is
    # unaffected and still loads.
    attributes = {r["id"]: r["identifier"] for r in fetch_csv_optional("item_attributes")}
    fling_effects = {r["id"]: r["identifier"] for r in fetch_csv("item_fling_effects")}

    attr_rows = []
    for r in fetch_csv_optional("item_attributes_map"):
        item = items.get(r["item_id"])
        attr = attributes.get(r["item_attribute_id"])
        if not item or not attr:
            continue
        attr_rows.append((item["identifier"], attr))
    if attr_rows:
        conn.executemany(
            "INSERT INTO item_attributes (item_identifier, attribute) "
            "VALUES (?,?) ON CONFLICT (item_identifier, attribute) DO NOTHING",
            attr_rows,
        )

    # Baby trigger derivation:
    #   evolution_chains.baby_trigger_item_id -> the incense the parent holds
    #   pokemon_species in that chain with is_baby='1' -> the baby species
    baby_species_by_chain: dict[str, str] = {}
    for s in fetch_csv("pokemon_species"):
        if s.get("is_baby") == "1":
            baby_species_by_chain[s["evolution_chain_id"]] = s["identifier"]

    baby_trigger: dict[str, str] = {}
    for c in fetch_csv("evolution_chains"):
        item_id = c.get("baby_trigger_item_id") or ""
        if not item_id:
            continue
        item = items.get(item_id)
        baby = baby_species_by_chain.get(c["id"])
        if item and baby:
            baby_trigger[item["identifier"]] = baby

    extra_rows = []
    for r in fetch_csv("items"):
        ident = r["identifier"]
        fp = int_or_none(r.get("fling_power"))
        fe = fling_effects.get(r.get("fling_effect_id")) if r.get("fling_effect_id") else None
        bt = baby_trigger.get(ident)
        if fp is None and fe is None and bt is None:
            continue
        extra_rows.append((ident, fp, fe, bt))
    if extra_rows:
        conn.executemany(
            """
            INSERT INTO item_extra
                (item_identifier, fling_power, fling_effect, baby_trigger_for)
            VALUES (?,?,?,?)
            ON CONFLICT (item_identifier) DO UPDATE SET
                fling_power      = excluded.fling_power,
                fling_effect     = excluded.fling_effect,
                baby_trigger_for = excluded.baby_trigger_for
            """,
            extra_rows,
        )

    conn.commit()
    return len(attr_rows), len(extra_rows)


def load_moves_canonical(conn) -> int:
    """Populate moves_canonical from PokeAPI's moves.csv.

    Canonical source for move type/damage_class/etc keyed by PokeAPI
    identifier — the join target for pokemon_moves_vg.
    """
    types = {r["id"]: r["identifier"] for r in fetch_csv("types")}
    damage_classes = {r["id"]: r["identifier"] for r in fetch_csv("move_damage_classes")}
    targets = {r["id"]: r["identifier"] for r in fetch_csv("move_targets")}
    generations = {r["id"]: int_or_none(r["id"]) for r in fetch_csv("generations")}

    rows = []
    for r in fetch_csv("moves"):
        rows.append((
            r["identifier"],
            types.get(r["type_id"]),
            damage_classes.get(r["damage_class_id"]),
            targets.get(r["target_id"]),
            int_or_none(r.get("power")),
            int_or_none(r.get("accuracy")),
            int_or_none(r.get("pp")),
            int_or_none(r.get("priority")),
            generations.get(r["generation_id"]),
        ))
    if rows:
        conn.executemany(
            """
            INSERT INTO moves_canonical (
                move_identifier, type, damage_class, target,
                power, accuracy, pp, priority, generation
            ) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT (move_identifier) DO UPDATE SET
                type         = excluded.type,
                damage_class = excluded.damage_class,
                target       = excluded.target,
                power        = excluded.power,
                accuracy     = excluded.accuracy,
                pp           = excluded.pp,
                priority     = excluded.priority,
                generation   = excluded.generation
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def load_pokemon_moves_vg(conn) -> int:
    """Load the per-version-group learnset from PokeAPI's pokemon_moves CSV.

    The largest CSV (~250k rows). Full refresh: DELETE then bulk insert, which
    is idempotent because the source is authoritative.
    """
    pokemon = index_by(fetch_csv("pokemon"), "id")
    moves = index_by(fetch_csv("moves"), "id")
    version_groups = {r["id"]: r["identifier"] for r in fetch_csv("version_groups")}
    methods = {r["id"]: r["identifier"] for r in fetch_csv("pokemon_move_methods")}

    conn.execute("DELETE FROM pokemon_moves_vg")

    # Dedupe on the table's primary key: PokeAPI can emit multiple
    # (pokemon, vg, move, method) rows differing only in level — keep the
    # lowest level (earliest learn), matching the Postgres loader.
    keyed: dict[tuple[str, str, str, str], tuple[int | None, int | None]] = {}
    for r in fetch_csv("pokemon_moves"):
        poke = pokemon.get(r["pokemon_id"])
        move = moves.get(r["move_id"])
        vg = version_groups.get(r["version_group_id"])
        method = methods.get(r["pokemon_move_method_id"])
        if not (poke and move and vg and method):
            continue
        key = (poke["identifier"], vg, move["identifier"], method)
        level = int_or_none(r.get("level"))
        order = int_or_none(r.get("order"))
        existing = keyed.get(key)
        if existing is None:
            keyed[key] = (level, order)
        else:
            old_level, old_order = existing
            if level is not None and (old_level is None or level < old_level):
                keyed[key] = (level, order if order is not None else old_order)

    conn.executemany(
        "INSERT INTO pokemon_moves_vg "
        "(pokemon_identifier, version_group, move_identifier, learn_method, "
        " level, move_order) VALUES (?,?,?,?,?,?)",
        [
            (poke_id, vg, move_id, method, level, order)
            for (poke_id, vg, move_id, method), (level, order) in keyed.items()
        ],
    )
    conn.commit()
    return len(keyed)


#: Ordered list of (label, callable) run by build_db.py.
LOADERS = [
    ("canonical moves", load_moves_canonical),
    ("move meta + stat changes", load_move_meta),
    ("past types", load_past_types),
    ("past abilities", load_past_abilities),
    ("item names", load_item_names),
    ("move names", load_move_names),
    ("ability names", load_ability_names),
    ("type names", load_type_names),
    ("item attributes + extras", load_item_attributes_and_extra),
    ("per-version-group learnset (large)", load_pokemon_moves_vg),
]


def run_all(conn: sqlite3.Connection) -> None:
    """Run every CSV loader in order against an already-schema'd connection."""
    for label, fn in LOADERS:
        print(f"Loading {label}...", flush=True)
        result = fn(conn)
        if isinstance(result, tuple):
            print(f"  {result[0]} attribute rows, {result[1]} extra rows", flush=True)
        else:
            print(f"  {result} rows", flush=True)
