"""Per-feature CSV loaders.

Each loader is a function that takes a psycopg2 cursor and upserts data into
one or more new tables. They run idempotently — re-running the loader fully
refreshes the data.
"""
from __future__ import annotations

from psycopg2.extras import execute_values

from .csv_fetch import fetch_csv, index_by

# PokeAPI internal IDs for damage classes / contest types / etc are stable
# across dumps. Resolving them via *_prose CSVs would be cleaner but for our
# purposes name → identifier is the only mapping we need, which is in the
# main entity CSVs themselves.


def load_move_meta(cur) -> int:
    """Load move_meta + move_stat_changes from PokeAPI CSV.

    Returns the number of move_meta rows inserted.
    """
    moves = index_by(fetch_csv("moves"), "id")
    ailments = {row["id"]: row["identifier"] for row in fetch_csv("move_meta_ailments")}
    categories = {row["id"]: row["identifier"] for row in fetch_csv("move_meta_categories")}
    stats = {row["id"]: row["identifier"] for row in fetch_csv("stats")}

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

    execute_values(
        cur,
        """
        INSERT INTO move_meta (
            move_identifier, ailment, ailment_chance, flinch_chance,
            crit_rate, drain, healing, stat_chance,
            min_hits, max_hits, min_turns, max_turns, category
        ) VALUES %s
        ON CONFLICT (move_identifier) DO UPDATE SET
            ailment = EXCLUDED.ailment,
            ailment_chance = EXCLUDED.ailment_chance,
            flinch_chance = EXCLUDED.flinch_chance,
            crit_rate = EXCLUDED.crit_rate,
            drain = EXCLUDED.drain,
            healing = EXCLUDED.healing,
            stat_chance = EXCLUDED.stat_chance,
            min_hits = EXCLUDED.min_hits,
            max_hits = EXCLUDED.max_hits,
            min_turns = EXCLUDED.min_turns,
            max_turns = EXCLUDED.max_turns,
            category = EXCLUDED.category
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
        # Wipe stat_changes for any move we touched, then re-insert. Clean and
        # avoids stale rows when PokeAPI revises data.
        touched_moves = {r[0] for r in stat_change_rows}
        execute_values(
            cur,
            "DELETE FROM move_stat_changes WHERE move_identifier IN (VALUES %s)",
            [(m,) for m in touched_moves],
        )
        execute_values(
            cur,
            "INSERT INTO move_stat_changes (move_identifier, stat, change) VALUES %s",
            stat_change_rows,
        )

    return len(meta_rows)


def load_past_types(cur) -> int:
    """Load pokemon_past_types from PokeAPI's pokemon_types_past CSV."""
    pokemon = index_by(fetch_csv("pokemon"), "id")
    types = {row["id"]: row["identifier"] for row in fetch_csv("types")}
    version_groups = index_by(fetch_csv("version_groups"), "id")
    rows = []
    for r in fetch_csv("pokemon_types_past"):
        poke = pokemon.get(r["pokemon_id"])
        type_ = types.get(r["type_id"])
        vg = version_groups.get(r["generation_id"]) if "generation_id" in r else None
        if not poke or not type_:
            continue
        # CSV uses generation_id, but column may be named differently in older
        # dumps. Default to generation_id; fall back to a version group lookup.
        gen_str = r.get("generation_id") or (vg["generation_id"] if vg else "")
        try:
            gen = int(gen_str)
        except (ValueError, TypeError):
            continue
        rows.append((poke["identifier"], gen, int(r["slot"]), type_))
    if rows:
        execute_values(
            cur,
            "INSERT INTO pokemon_past_types (pokemon_identifier, generation, slot, type) "
            "VALUES %s ON CONFLICT (pokemon_identifier, generation, slot) DO UPDATE "
            "SET type = EXCLUDED.type",
            rows,
        )
    return len(rows)


def load_past_abilities(cur) -> int:
    """Load pokemon_past_abilities from PokeAPI's pokemon_abilities_past CSV."""
    pokemon = index_by(fetch_csv("pokemon"), "id")
    abilities = {row["id"]: row["identifier"] for row in fetch_csv("abilities")}
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
        rows.append((poke["identifier"], gen, slot, ability, r["is_hidden"] == "1"))
    if rows:
        execute_values(
            cur,
            "INSERT INTO pokemon_past_abilities "
            "(pokemon_identifier, generation, slot, ability, is_hidden) "
            "VALUES %s ON CONFLICT (pokemon_identifier, generation, slot) DO UPDATE "
            "SET ability = EXCLUDED.ability, is_hidden = EXCLUDED.is_hidden",
            rows,
        )
    return len(rows)


def _load_localized_names(cur, *, entity_csv: str, names_csv: str, table: str, id_column: str) -> int:
    """Generic loader for entity_names tables.

    The names CSV uses (entity_id, local_language_id, name) plus a couple of
    other columns. We resolve entity_id → identifier and language_id → iso639
    identifier (e.g. "en", "ja", "fr").
    """
    entities = {row["id"]: row["identifier"] for row in fetch_csv(entity_csv)}
    languages = {row["id"]: row["identifier"] for row in fetch_csv("languages")}
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
    pk_col = {
        "item_names":    "item_identifier",
        "move_names":    "move_identifier",
        "ability_names": "ability_identifier",
        "type_names":    "type_identifier",
    }[table]
    execute_values(
        cur,
        f"INSERT INTO {table} ({pk_col}, language, localized_name) VALUES %s "
        f"ON CONFLICT ({pk_col}, language) DO UPDATE SET localized_name = EXCLUDED.localized_name",
        rows,
    )
    return len(rows)


def load_item_names(cur) -> int:
    return _load_localized_names(
        cur, entity_csv="items", names_csv="item_names",
        table="item_names", id_column="item_id",
    )


def load_move_names(cur) -> int:
    return _load_localized_names(
        cur, entity_csv="moves", names_csv="move_names",
        table="move_names", id_column="move_id",
    )


def load_ability_names(cur) -> int:
    return _load_localized_names(
        cur, entity_csv="abilities", names_csv="ability_names",
        table="ability_names", id_column="ability_id",
    )


def load_type_names(cur) -> int:
    return _load_localized_names(
        cur, entity_csv="types", names_csv="type_names",
        table="type_names", id_column="type_id",
    )


def load_item_attributes_and_extra(cur) -> tuple[int, int]:
    """Load item_attributes and item_extra (fling, baby_trigger)."""
    items = index_by(fetch_csv("items"), "id")
    attributes = {row["id"]: row["identifier"] for row in fetch_csv("item_attributes")}
    fling_effects = {
        row["id"]: row["identifier"] for row in fetch_csv("item_fling_effects")
    }

    # Item attribute mapping
    attr_rows = []
    for r in fetch_csv("item_attributes_map"):
        item = items.get(r["item_id"])
        attr = attributes.get(r["item_attribute_id"])
        if not item or not attr:
            continue
        attr_rows.append((item["identifier"], attr))
    if attr_rows:
        execute_values(
            cur,
            "INSERT INTO item_attributes (item_identifier, attribute) VALUES %s "
            "ON CONFLICT (item_identifier, attribute) DO NOTHING",
            attr_rows,
        )

    # Baby trigger derivation:
    #   evolution_chains.baby_trigger_item_id → the incense the parent must hold
    #   pokemon_species rows in that chain with is_baby='1' → the baby species
    species = list(fetch_csv("pokemon_species"))
    baby_species_by_chain: dict[str, str] = {}
    for s in species:
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
        execute_values(
            cur,
            """
            INSERT INTO item_extra (item_identifier, fling_power, fling_effect, baby_trigger_for)
            VALUES %s
            ON CONFLICT (item_identifier) DO UPDATE SET
                fling_power = EXCLUDED.fling_power,
                fling_effect = EXCLUDED.fling_effect,
                baby_trigger_for = EXCLUDED.baby_trigger_for
            """,
            extra_rows,
        )

    return len(attr_rows), len(extra_rows)


def load_moves_canonical(cur) -> int:
    """Populate moves_canonical from PokeAPI's moves.csv.

    This is the canonical source for move type/damage_class/etc keyed by
    PokeAPI identifier — used as the join target for pokemon_moves_vg so we
    don't rely on translating pokemondb display names.
    """
    types = {row["id"]: row["identifier"] for row in fetch_csv("types")}
    damage_classes = {
        row["id"]: row["identifier"] for row in fetch_csv("move_damage_classes")
    }
    targets = {row["id"]: row["identifier"] for row in fetch_csv("move_targets")}
    generations = {
        row["id"]: int_or_none(row["id"]) for row in fetch_csv("generations")
    }

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
        execute_values(
            cur,
            """
            INSERT INTO moves_canonical (
                move_identifier, type, damage_class, target,
                power, accuracy, pp, priority, generation
            ) VALUES %s
            ON CONFLICT (move_identifier) DO UPDATE SET
                type = EXCLUDED.type,
                damage_class = EXCLUDED.damage_class,
                target = EXCLUDED.target,
                power = EXCLUDED.power,
                accuracy = EXCLUDED.accuracy,
                pp = EXCLUDED.pp,
                priority = EXCLUDED.priority,
                generation = EXCLUDED.generation
            """,
            rows,
        )
    return len(rows)


def load_pokemon_moves_vg(cur) -> int:
    """Load per-version-group learnset from PokeAPI's pokemon_moves CSV.

    The largest CSV (~250k rows). We TRUNCATE and stream via COPY FROM for
    speed — full refresh, idempotent because the source is authoritative.
    Same-key rows would have collapsed under the previous ON CONFLICT branch
    anyway, so no information is lost.
    """
    import io

    pokemon = index_by(fetch_csv("pokemon"), "id")
    moves = index_by(fetch_csv("moves"), "id")
    version_groups = {row["id"]: row["identifier"] for row in fetch_csv("version_groups")}
    methods = {row["id"]: row["identifier"] for row in fetch_csv("pokemon_move_methods")}

    cur.execute("TRUNCATE pokemon_moves_vg")

    # Build a deduped buffer keyed by the table's primary key, since
    # PokeAPI's pokemon_moves can have multiple (pokemon, vg, move, method)
    # rows differing only in level — we keep the lowest level (earliest
    # learn) which matches the previous ON CONFLICT semantics.
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
            # Prefer the smaller (or only) level
            if level is not None and (old_level is None or level < old_level):
                keyed[key] = (level, order if order is not None else old_order)

    NULL = "\\N"  # PostgreSQL COPY null marker
    buf = io.StringIO()
    for (poke_id, vg, move_id, method), (level, order) in keyed.items():
        level_s = str(level) if level is not None else NULL
        order_s = str(order) if order is not None else NULL
        buf.write(f"{poke_id}\t{vg}\t{move_id}\t{method}\t{level_s}\t{order_s}\n")
    buf.seek(0)
    cur.copy_expert(
        "COPY pokemon_moves_vg "
        "(pokemon_identifier, version_group, move_identifier, learn_method, level, move_order) "
        "FROM STDIN WITH (FORMAT text)",
        buf,
    )
    return len(keyed)


def int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None
