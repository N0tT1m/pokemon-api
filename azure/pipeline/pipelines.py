"""Scrapy item pipeline writing to SQLite, for the Azure ingest path.

Mirrors pokemondb_scraper/pokemondb_scraper/pipelines.py:PostgresPipeline one
item type for one item type, but routes every write through writer.py into a
SQLite file instead of Postgres. The existing Postgres pipeline is untouched;
this is a parallel implementation.

Items are dispatched on the item class *name* rather than on an isinstance
check, so this module has no import dependency on pokemondb_scraper.items and
can be used with the spiders as-is.

Wire it up by pointing Scrapy at this module, e.g.:

    ITEM_PIPELINES = {"pipelines.SQLitePipeline": 300}
    POKEDEX_DB_PATH = "pokedex.db"
"""
from __future__ import annotations

from typing import Any, Mapping

try:
    from itemadapter import ItemAdapter
except ImportError:  # Scrapy not installed — SPECS/write_item still usable.
    ItemAdapter = None

import writer
from writer import json_array_union

# ---------------------------------------------------------------------------
# Declarative upsert specs: item class name -> (table, writer.upsert kwargs)
#
# These reproduce, one-for-one, the ON CONFLICT clauses in the Postgres
# pipeline. "update" = SET c = EXCLUDED.c, "coalesce" = SET c = COALESCE(...),
# "or_merge" = boolean OR, do_nothing = DO NOTHING.
# ---------------------------------------------------------------------------

_POKEMON_COLS = [
    "url", "national_no", "types", "species", "height", "weight", "abilities",
    "ev_yield", "catch_rate", "base_friendship", "base_exp", "growth_rate",
    "egg_groups", "gender_ratio", "egg_cycles", "hp", "attack", "defense",
    "sp_atk", "sp_def", "speed", "total",
]

SPECS: dict[str, tuple[str, dict[str, Any]]] = {
    "PokemonItem": ("pokemon", {
        "conflict": ["name"],
        "update": _POKEMON_COLS,
    }),
    "TypeDefenseItem": ("type_defenses", {
        "conflict": ["pokemon_name", "type_name"],
        "update": ["multiplier"],
    }),
    "EvolutionItem": ("evolutions", {
        "conflict": ["pokemon_name", "evo_name", "COALESCE(evolves_from, '')"],
        "do_nothing": True,
    }),
    # moves / locations have no unique constraint upstream -> plain INSERT.
    "MoveItem": ("moves", None),
    "LocationItem": ("locations", None),
    "RegionalDexItem": ("regional_dex", {
        "conflict": ["game", "pokemon_name"],
        "update": ["dex_number", "types"],
    }),
    "GameNationalDexItem": ("game_national_dex", {
        "conflict": ["game", "pokemon_name"],
        "update": ["national_no"],
    }),
    "GameItemDetail": ("item_details", {
        "conflict": ["name"],
        "update": ["category", "effect", "sprite_url"],
        "coalesce": ["buy_price", "sell_price"],
    }),
    "MoveDetail": ("move_details", {
        "conflict": ["name"],
        "update": ["type", "category", "power", "accuracy", "pp", "effect",
                   "effect_chance"],
        "coalesce": ["priority", "target", "generation_introduced",
                     "z_move_equivalent", "max_move_equivalent",
                     "contest_type", "flags"],
    }),
    "AbilityDetail": ("ability_details", {
        "conflict": ["name"],
        "update": ["description", "generation"],
    }),
    "AbilityPokemonItem": ("ability_pokemon", {
        "conflict": ["ability_name", "pokemon_name"],
        "update": ["is_hidden"],
    }),
    "PokedexEntryItem": ("pokedex_entries", {
        "conflict": ["pokemon_name", "game_version"],
        "update": ["flavor_text"],
    }),
    "NatureItem": ("natures", {
        "conflict": ["name"],
        "update": ["increased_stat", "decreased_stat"],
    }),
    "LocationEncounterItem": ("location_encounters", {
        "conflict": ["region", "route_name", "pokemon_name",
                     "COALESCE(encounter_method, '')"],
        "coalesce": ["rarity", "level_range", "time_of_day"],
        "set_raw": {"games": json_array_union("location_encounters", "games")},
    }),
    "BerryItem": ("berries", {
        "conflict": ["name"],
        "update": ["natural_gift_type", "natural_gift_power", "size_mm",
                   "firmness", "effect", "growth_time"],
    }),
    "BerryFlavorItem": ("berry_flavors", {
        "conflict": ["berry_name", "flavor"],
        "update": ["potency"],
    }),
    "ItemLocationItem": ("item_locations", {
        "conflict": ["item_name", "game", "location"],
        "do_nothing": True,
    }),
    "TmLocationItem": ("tm_locations", {
        "conflict": ["tm_number", "game", "move_name"],
        "do_nothing": True,
    }),
    "PokemonNameItem": ("pokemon_names", {
        "conflict": ["pokemon_name", "language"],
        "update": ["localized_name"],
    }),
    "PokemonSpriteItem": ("pokemon_sprites", {
        "conflict": ["pokemon_name", "sprite_type", "url",
                     "COALESCE(generation, '')"],
        "do_nothing": True,
    }),
    "WildHeldItemItem": ("wild_held_items", {
        "conflict": ["pokemon_name", "game", "item_name"],
        "update": ["rarity"],
    }),
    "PokemonBiologyItem": ("pokemon_biology", {
        "conflict": ["pokemon_name"],
        "update": ["biology"],
    }),
    "PokemonGameLocationItem": ("pokemon_game_locations", {
        "conflict": ["pokemon_name", "game", "location"],
        "coalesce": ["method"],
    }),
    "RaidEventItem": ("raid_events", {
        "conflict": ["pokemon_name", "COALESCE(tera_type, '')",
                     "COALESCE(event_start, '')"],
        "update": ["star_rating", "event_end", "is_active", "source_url"],
        # Postgres refreshed scraped_at = NOW() on conflict.
        "set_raw": {"scraped_at": "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"},
    }),
    "RaidCounterItem": ("raid_counters", {
        "conflict": ["pokemon_name", "COALESCE(tera_type, '')",
                     "counter_pokemon"],
        "update": ["rank", "notes"],
    }),
    "PokemonFormItem": ("pokemon_forms", {
        "conflict": ["pokemon_name", "form_name"],
        "update": ["types", "abilities", "height", "weight", "hp", "attack",
                   "defense", "sp_atk", "sp_def", "speed", "total"],
    }),
    "EggMovePokemonItem": ("egg_move_parents", {
        "conflict": ["pokemon_name", "move_name", "parent_name"],
        "do_nothing": True,
    }),
    "TrainerItem": ("trainers", {
        "conflict": ["name", "game", "battle_variant"],
        "coalesce": ["role", "specialty_type", "location"],
    }),
    "TrainerPokemonItem": ("trainer_pokemon", {
        "conflict": ["trainer_name", "game", "battle_variant", "team_order"],
        "update": ["pokemon_name", "level"],
        "coalesce": ["held_item", "ability", "moves"],
    }),
    "PokemonClassificationItem": ("pokemon_classification", {
        "conflict": ["pokemon_name"],
        "coalesce": ["generation_introduced", "color", "shape", "habitat"],
        "or_merge": ["is_legendary", "is_mythical", "is_ultra_beast",
                     "is_baby", "is_paradox"],
    }),
    "ZMoveItem": ("z_moves", {
        "conflict": ["name"],
        "update": ["type"],
        "coalesce": ["power", "effect", "base_move", "category"],
    }),
    "InGameTradeItem": ("in_game_trades", {
        "conflict": ["game", "offered_pokemon", "requested_pokemon"],
        "coalesce": ["location", "offered_level", "offered_item", "npc_name",
                     "notes"],
    }),
    "ContestStatItem": ("contest_stats", {
        "conflict": ["pokemon_name", "contest_type"],
        "coalesce": ["appeal", "jam"],
    }),
    "EventPokemonItem": ("event_pokemon", {
        "conflict": ["name", "COALESCE(game, '')", "COALESCE(ot_name, '')",
                     "COALESCE(CAST(year AS TEXT), '')"],
        "coalesce": ["level", "held_item", "moves", "distribution_method",
                     "notes"],
    }),
    "MassOutbreakItem": ("mass_outbreaks", {
        "conflict": ["game", "pokemon_name", "COALESCE(location, '')"],
        "coalesce": ["region", "notes"],
    }),
    "PokemonGoItem": ("pokemon_go", {
        "conflict": ["pokemon_name"],
        "coalesce": ["max_cp", "buddy_distance_km", "base_attack",
                     "base_defense", "base_stamina"],
        "or_merge": ["shiny_available", "shadow_available"],
    }),
    "BattleFacilityItem": ("battle_facilities", {
        "conflict": ["name", "game"],
        "coalesce": ["region", "facility_type", "description", "currency"],
    }),
    "MoveTutorLocationItem": ("move_tutor_locations", {
        "conflict": ["move_name", "game", "COALESCE(location, '')"],
        "coalesce": ["cost"],
    }),
    "VersionExclusiveItem": ("version_exclusives", {
        "conflict": ["pokemon_name", "game"],
        "coalesce": ["game_pair"],
    }),
}

# Columns the Postgres pipeline explicitly defaulted to None when a spider
# omitted them, so that COALESCE-on-conflict has something to compare.
_DEFAULTED: dict[str, tuple[str, ...]] = {
    "MoveDetail": ("generation_introduced", "z_move_equivalent",
                   "max_move_equivalent", "contest_type", "flags"),
}


def write_item(conn, item_name: str, data: Mapping[str, Any]) -> bool:
    """Write one item dict. Returns False if the item type is unknown."""
    spec = SPECS.get(item_name)
    if spec is None:
        return False
    table, kwargs = spec
    row = dict(data)
    for col in _DEFAULTED.get(item_name, ()):
        row.setdefault(col, None)
    if kwargs is None:
        writer.insert(conn, table, row)
    else:
        writer.upsert(conn, table, row, **kwargs)
    return True


class SQLitePipeline:
    """Scrapy item pipeline writing to SQLite via writer.py."""

    #: commit every N items rather than per item — the Postgres pipeline
    #: committed per item, which is needlessly slow against a local file.
    COMMIT_EVERY = 500

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._pending = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_path=crawler.settings.get("POKEDEX_DB_PATH", writer.DEFAULT_DB_PATH),
        )

    def open_spider(self, spider):
        self.conn = writer.open_db(self.db_path)
        writer.apply_schema(self.conn)
        writer.seed_type_matchups(self.conn)

    def close_spider(self, spider):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None

    def process_item(self, item, spider):
        if ItemAdapter is None:
            raise RuntimeError("itemadapter is required to run SQLitePipeline")
        adapter = ItemAdapter(item)
        write_item(self.conn, type(item).__name__, dict(adapter))
        self._pending += 1
        if self._pending >= self.COMMIT_EVERY:
            self.conn.commit()
            self._pending = 0
        return item
