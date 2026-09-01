"""SQLite schema for the Azure variant of the Pokedex database.

This is a translation of the two Postgres schemas that feed the original
deployment:

  * pokemondb_scraper/pokemondb_scraper/pipelines.py  (40 tables)
  * pokeapi_csv_loader/pokeapi_csv_loader/schema.py   (12 tables)

52 tables total. Translation rules applied:

  TEXT[]                 -> TEXT holding a JSON array, e.g. '["Water","Ice"]'.
                            Never Postgres '{a,b}' literals, never NULL where
                            an empty array is meant -- write '[]'. The Go read
                            side parses these with json_each / json.Unmarshal.
  SERIAL / BIGSERIAL     -> INTEGER PRIMARY KEY AUTOINCREMENT
  TIMESTAMP/TIMESTAMPTZ  -> TEXT storing ISO-8601 UTC ('2026-07-18T12:34:56Z')
  BOOLEAN                -> INTEGER 0/1
  ALTER TABLE ... ADD
    COLUMN IF NOT EXISTS -> folded into the base CREATE TABLE

All primary keys, unique constraints and indexes from the sources are
preserved. Additional indexes are added for every column db/queries.go filters
or joins on, including LOWER()-expression indexes for the case-insensitive
lookups that file performs.

Note on foreign keys: the Postgres sources declare REFERENCES ... ON DELETE
CASCADE on several tables. They are preserved here, but PRAGMA foreign_keys is
left OFF during load (see writer.py) so that ingest order does not matter --
the same effective behaviour as the original, which committed per item.
"""

SCHEMA_SQL = """
-- ---------------------------------------------------------------------------
-- Core Pokemon data (pokemondb_scraper)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pokemon (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    url             TEXT,
    national_no     TEXT,
    types           TEXT NOT NULL DEFAULT '[]',   -- JSON array
    species         TEXT,
    height          TEXT,
    weight          TEXT,
    abilities       TEXT NOT NULL DEFAULT '[]',   -- JSON array
    ev_yield        TEXT,
    catch_rate      TEXT,
    base_friendship TEXT,
    base_exp        TEXT,
    growth_rate     TEXT,
    egg_groups      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    gender_ratio    TEXT,
    egg_cycles      TEXT,
    hp              INTEGER,
    attack          INTEGER,
    defense         INTEGER,
    sp_atk          INTEGER,
    sp_def          INTEGER,
    speed           INTEGER,
    total           INTEGER
);

CREATE INDEX IF NOT EXISTS pokemon_lower_name_idx   ON pokemon (LOWER(name));
CREATE INDEX IF NOT EXISTS pokemon_national_no_idx  ON pokemon (national_no);

CREATE TABLE IF NOT EXISTS type_defenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    type_name    TEXT NOT NULL,
    multiplier   REAL NOT NULL DEFAULT 1.0,
    UNIQUE(pokemon_name, type_name)
);

CREATE INDEX IF NOT EXISTS type_defenses_pokemon_idx ON type_defenses (pokemon_name);

CREATE TABLE IF NOT EXISTS evolutions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    number       TEXT,
    evo_name     TEXT NOT NULL,
    evo_url      TEXT,
    types        TEXT NOT NULL DEFAULT '[]',   -- JSON array
    evolves_via  TEXT,
    evolves_from TEXT,
    chain_order  INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS evolutions_unique_entry
    ON evolutions (pokemon_name, evo_name, COALESCE(evolves_from, ''));
CREATE INDEX IF NOT EXISTS evolutions_pokemon_idx ON evolutions (pokemon_name, chain_order);

CREATE TABLE IF NOT EXISTS moves (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    learn_method TEXT NOT NULL,
    level_or_tm  TEXT,
    move_name    TEXT NOT NULL,
    type         TEXT,
    category     TEXT,
    power        INTEGER,
    accuracy     INTEGER
);

CREATE INDEX IF NOT EXISTS moves_pokemon_idx         ON moves (pokemon_name, learn_method, level_or_tm);
CREATE INDEX IF NOT EXISTS moves_lower_move_name_idx ON moves (LOWER(move_name));

CREATE TABLE IF NOT EXISTS locations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    games        TEXT NOT NULL DEFAULT '[]',   -- JSON array
    locations    TEXT NOT NULL DEFAULT '[]'    -- JSON array
);

CREATE INDEX IF NOT EXISTS locations_pokemon_idx ON locations (pokemon_name);

CREATE TABLE IF NOT EXISTS regional_dex (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game         TEXT NOT NULL,
    dex_number   INTEGER NOT NULL,
    pokemon_name TEXT NOT NULL,
    types        TEXT NOT NULL DEFAULT '[]',   -- JSON array
    UNIQUE(game, pokemon_name)
);

CREATE INDEX IF NOT EXISTS regional_dex_game_idx ON regional_dex (game, dex_number);

CREATE TABLE IF NOT EXISTS game_national_dex (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game         TEXT NOT NULL,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    national_no  INTEGER NOT NULL,
    UNIQUE(game, pokemon_name)
);

CREATE INDEX IF NOT EXISTS game_national_dex_game_idx ON game_national_dex (game, national_no);

CREATE TABLE IF NOT EXISTS item_details (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT,
    effect      TEXT,
    sprite_url  TEXT,
    buy_price   INTEGER,
    sell_price  INTEGER
);

CREATE INDEX IF NOT EXISTS item_details_lower_name_idx ON item_details (LOWER(name));

CREATE TABLE IF NOT EXISTS move_details (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL UNIQUE,
    type                  TEXT,
    category              TEXT,
    power                 INTEGER,
    accuracy              INTEGER,
    pp                    INTEGER,
    effect                TEXT,
    effect_chance         INTEGER,
    priority              INTEGER,
    target                TEXT,
    generation_introduced INTEGER,
    z_move_equivalent     TEXT,
    max_move_equivalent   TEXT,
    contest_type          TEXT,
    flags                 TEXT NOT NULL DEFAULT '[]'   -- JSON array
);

CREATE INDEX IF NOT EXISTS move_details_lower_name_idx     ON move_details (LOWER(name));
CREATE INDEX IF NOT EXISTS move_details_lower_type_idx     ON move_details (LOWER(type));
CREATE INDEX IF NOT EXISTS move_details_lower_category_idx ON move_details (LOWER(category));
CREATE INDEX IF NOT EXISTS move_details_generation_idx     ON move_details (generation_introduced);

CREATE TABLE IF NOT EXISTS ability_details (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    generation  INTEGER
);

CREATE INDEX IF NOT EXISTS ability_details_lower_name_idx ON ability_details (LOWER(name));

CREATE TABLE IF NOT EXISTS ability_pokemon (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ability_name  TEXT NOT NULL REFERENCES ability_details(name) ON DELETE CASCADE,
    pokemon_name  TEXT NOT NULL,
    is_hidden     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(ability_name, pokemon_name)
);

CREATE INDEX IF NOT EXISTS ability_pokemon_lower_ability_idx ON ability_pokemon (LOWER(ability_name));
CREATE INDEX IF NOT EXISTS ability_pokemon_lower_pokemon_idx ON ability_pokemon (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS pokedex_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    game_version TEXT NOT NULL,
    flavor_text  TEXT NOT NULL,
    UNIQUE(pokemon_name, game_version)
);

CREATE INDEX IF NOT EXISTS pokedex_entries_pokemon_idx ON pokedex_entries (pokemon_name, game_version);

CREATE TABLE IF NOT EXISTS natures (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    increased_stat TEXT,
    decreased_stat TEXT
);

CREATE TABLE IF NOT EXISTS location_encounters (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    region           TEXT NOT NULL,
    route_name       TEXT NOT NULL,
    pokemon_name     TEXT NOT NULL,
    games            TEXT NOT NULL DEFAULT '[]',   -- JSON array
    encounter_method TEXT,
    rarity           TEXT,
    level_range      TEXT,
    time_of_day      TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS location_encounters_unique
    ON location_encounters (region, route_name, pokemon_name, COALESCE(encounter_method, ''));
CREATE INDEX IF NOT EXISTS location_encounters_lower_region_idx  ON location_encounters (LOWER(region));
CREATE INDEX IF NOT EXISTS location_encounters_lower_route_idx   ON location_encounters (LOWER(region), LOWER(route_name));
CREATE INDEX IF NOT EXISTS location_encounters_lower_pokemon_idx ON location_encounters (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS berries (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL UNIQUE,
    natural_gift_type  TEXT,
    natural_gift_power INTEGER,
    size_mm            INTEGER,
    firmness           TEXT,
    effect             TEXT,
    growth_time        INTEGER
);

CREATE INDEX IF NOT EXISTS berries_lower_name_idx ON berries (LOWER(name));

CREATE TABLE IF NOT EXISTS berry_flavors (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    berry_name TEXT NOT NULL REFERENCES berries(name) ON DELETE CASCADE,
    flavor     TEXT NOT NULL,
    potency    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(berry_name, flavor)
);

CREATE INDEX IF NOT EXISTS berry_flavors_lower_berry_idx ON berry_flavors (LOWER(berry_name));

CREATE TABLE IF NOT EXISTS item_locations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    game      TEXT NOT NULL,
    location  TEXT NOT NULL,
    method    TEXT,
    UNIQUE(item_name, game, location)
);

CREATE INDEX IF NOT EXISTS item_locations_lower_item_idx ON item_locations (LOWER(item_name));
CREATE INDEX IF NOT EXISTS item_locations_game_idx       ON item_locations (game, item_name);

CREATE TABLE IF NOT EXISTS tm_locations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tm_number TEXT NOT NULL,
    move_name TEXT NOT NULL,
    game      TEXT NOT NULL,
    location  TEXT NOT NULL,
    UNIQUE(tm_number, game, move_name)
);

CREATE INDEX IF NOT EXISTS tm_locations_game_idx ON tm_locations (game, tm_number);

CREATE TABLE IF NOT EXISTS pokemon_names (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name   TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    language       TEXT NOT NULL,
    localized_name TEXT NOT NULL,
    UNIQUE(pokemon_name, language)
);

CREATE INDEX IF NOT EXISTS pokemon_names_pokemon_idx ON pokemon_names (pokemon_name, language);

CREATE TABLE IF NOT EXISTS pokemon_sprites (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    sprite_type  TEXT NOT NULL,
    generation   TEXT,
    url          TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pokemon_sprites_unique
    ON pokemon_sprites (pokemon_name, sprite_type, url, COALESCE(generation, ''));
CREATE INDEX IF NOT EXISTS pokemon_sprites_pokemon_idx ON pokemon_sprites (pokemon_name, generation, sprite_type);

CREATE TABLE IF NOT EXISTS wild_held_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    game         TEXT NOT NULL,
    item_name    TEXT NOT NULL,
    rarity       TEXT,
    UNIQUE(pokemon_name, game, item_name)
);

CREATE INDEX IF NOT EXISTS wild_held_items_lower_pokemon_idx ON wild_held_items (LOWER(pokemon_name));
CREATE INDEX IF NOT EXISTS wild_held_items_lower_item_idx    ON wild_held_items (LOWER(item_name));

CREATE TABLE IF NOT EXISTS pokemon_biology (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL UNIQUE,
    biology      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS pokemon_biology_lower_pokemon_idx ON pokemon_biology (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS pokemon_game_locations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    game         TEXT NOT NULL,
    location     TEXT NOT NULL,
    method       TEXT,
    UNIQUE(pokemon_name, game, location)
);

CREATE INDEX IF NOT EXISTS pokemon_game_locations_lower_pokemon_idx
    ON pokemon_game_locations (LOWER(pokemon_name));
CREATE INDEX IF NOT EXISTS pokemon_game_locations_game_idx ON pokemon_game_locations (game);

CREATE TABLE IF NOT EXISTS raid_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    tera_type    TEXT,
    star_rating  INTEGER,
    event_start  TEXT,
    event_end    TEXT,
    is_active    INTEGER NOT NULL DEFAULT 0,
    source_url   TEXT,
    -- ISO-8601 UTC, e.g. 2026-07-18T12:34:56Z
    scraped_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS raid_events_unique
    ON raid_events (pokemon_name, COALESCE(tera_type, ''), COALESCE(event_start, ''));
CREATE INDEX IF NOT EXISTS raid_events_lower_pokemon_idx ON raid_events (LOWER(pokemon_name));
CREATE INDEX IF NOT EXISTS raid_events_active_idx        ON raid_events (is_active, scraped_at);

CREATE TABLE IF NOT EXISTS raid_counters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name    TEXT NOT NULL,
    tera_type       TEXT,
    counter_pokemon TEXT NOT NULL,
    "rank"          INTEGER,
    notes           TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS raid_counters_unique
    ON raid_counters (pokemon_name, COALESCE(tera_type, ''), counter_pokemon);
CREATE INDEX IF NOT EXISTS raid_counters_lower_pokemon_idx ON raid_counters (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS pokemon_forms (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    form_name    TEXT NOT NULL,
    types        TEXT NOT NULL DEFAULT '[]',   -- JSON array
    abilities    TEXT NOT NULL DEFAULT '[]',   -- JSON array
    height       TEXT,
    weight       TEXT,
    hp           INTEGER,
    attack       INTEGER,
    defense      INTEGER,
    sp_atk       INTEGER,
    sp_def       INTEGER,
    speed        INTEGER,
    total        INTEGER,
    UNIQUE(pokemon_name, form_name)
);

CREATE INDEX IF NOT EXISTS pokemon_forms_lower_pokemon_idx ON pokemon_forms (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS egg_move_parents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    move_name    TEXT NOT NULL,
    parent_name  TEXT NOT NULL,
    UNIQUE(pokemon_name, move_name, parent_name)
);

CREATE INDEX IF NOT EXISTS egg_move_parents_lower_pokemon_idx
    ON egg_move_parents (LOWER(pokemon_name));
CREATE INDEX IF NOT EXISTS egg_move_parents_lower_pokemon_move_idx
    ON egg_move_parents (LOWER(pokemon_name), LOWER(move_name));

CREATE TABLE IF NOT EXISTS pokemon_classification (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name          TEXT NOT NULL UNIQUE,
    generation_introduced INTEGER,
    is_legendary          INTEGER NOT NULL DEFAULT 0,
    is_mythical           INTEGER NOT NULL DEFAULT 0,
    is_ultra_beast        INTEGER NOT NULL DEFAULT 0,
    is_baby               INTEGER NOT NULL DEFAULT 0,
    is_paradox            INTEGER NOT NULL DEFAULT 0,
    color                 TEXT,
    shape                 TEXT,
    habitat               TEXT
);

CREATE INDEX IF NOT EXISTS pokemon_classification_lower_pokemon_idx
    ON pokemon_classification (LOWER(pokemon_name));
CREATE INDEX IF NOT EXISTS pokemon_classification_lower_color_idx   ON pokemon_classification (LOWER(color));
CREATE INDEX IF NOT EXISTS pokemon_classification_lower_shape_idx   ON pokemon_classification (LOWER(shape));
CREATE INDEX IF NOT EXISTS pokemon_classification_lower_habitat_idx ON pokemon_classification (LOWER(habitat));

CREATE TABLE IF NOT EXISTS z_moves (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    type      TEXT,
    power     INTEGER,
    effect    TEXT,
    base_move TEXT,
    category  TEXT
);

CREATE INDEX IF NOT EXISTS z_moves_lower_name_idx ON z_moves (LOWER(name));

CREATE TABLE IF NOT EXISTS in_game_trades (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    game              TEXT NOT NULL,
    location          TEXT,
    offered_pokemon   TEXT NOT NULL,
    offered_level     INTEGER,
    offered_item      TEXT,
    requested_pokemon TEXT NOT NULL,
    npc_name          TEXT,
    notes             TEXT,
    UNIQUE(game, offered_pokemon, requested_pokemon)
);

CREATE INDEX IF NOT EXISTS in_game_trades_lower_game_idx ON in_game_trades (LOWER(game));

CREATE TABLE IF NOT EXISTS contest_stats (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    contest_type TEXT NOT NULL,
    appeal       INTEGER,
    jam          INTEGER,
    UNIQUE(pokemon_name, contest_type)
);

CREATE INDEX IF NOT EXISTS contest_stats_lower_pokemon_idx ON contest_stats (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS event_pokemon (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    game                TEXT,
    year                INTEGER,
    level               INTEGER,
    held_item           TEXT,
    moves               TEXT NOT NULL DEFAULT '[]',   -- JSON array
    ot_name             TEXT,
    distribution_method TEXT,
    notes               TEXT
);

-- Postgres used COALESCE(year::TEXT, ''); CAST(year AS TEXT) is the SQLite
-- equivalent and yields the same '' for NULL via COALESCE.
CREATE UNIQUE INDEX IF NOT EXISTS event_pokemon_unique
    ON event_pokemon (name, COALESCE(game, ''), COALESCE(ot_name, ''), COALESCE(CAST(year AS TEXT), ''));
CREATE INDEX IF NOT EXISTS event_pokemon_lower_name_idx ON event_pokemon (LOWER(name));
CREATE INDEX IF NOT EXISTS event_pokemon_lower_game_idx ON event_pokemon (LOWER(game));

CREATE TABLE IF NOT EXISTS mass_outbreaks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game         TEXT NOT NULL,
    region       TEXT,
    location     TEXT,
    pokemon_name TEXT NOT NULL,
    notes        TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS mass_outbreaks_unique
    ON mass_outbreaks (game, pokemon_name, COALESCE(location, ''));
CREATE INDEX IF NOT EXISTS mass_outbreaks_lower_game_idx   ON mass_outbreaks (LOWER(game));
CREATE INDEX IF NOT EXISTS mass_outbreaks_lower_region_idx ON mass_outbreaks (LOWER(region));

CREATE TABLE IF NOT EXISTS pokemon_go (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name      TEXT NOT NULL UNIQUE,
    max_cp            INTEGER,
    buddy_distance_km INTEGER,
    base_attack       INTEGER,
    base_defense      INTEGER,
    base_stamina      INTEGER,
    shiny_available   INTEGER NOT NULL DEFAULT 0,
    shadow_available  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS pokemon_go_lower_pokemon_idx ON pokemon_go (LOWER(pokemon_name));

CREATE TABLE IF NOT EXISTS battle_facilities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    game          TEXT NOT NULL,
    region        TEXT,
    facility_type TEXT,
    description   TEXT,
    currency      TEXT,
    UNIQUE(name, game)
);

CREATE INDEX IF NOT EXISTS battle_facilities_lower_game_idx ON battle_facilities (LOWER(game));

CREATE TABLE IF NOT EXISTS move_tutor_locations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    move_name TEXT NOT NULL,
    game      TEXT NOT NULL,
    location  TEXT,
    cost      TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS move_tutor_locations_unique
    ON move_tutor_locations (move_name, game, COALESCE(location, ''));
CREATE INDEX IF NOT EXISTS move_tutor_locations_lower_game_idx ON move_tutor_locations (LOWER(game));
CREATE INDEX IF NOT EXISTS move_tutor_locations_lower_move_idx ON move_tutor_locations (LOWER(move_name));

CREATE TABLE IF NOT EXISTS version_exclusives (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_name TEXT NOT NULL,
    game         TEXT NOT NULL,
    game_pair    TEXT,
    UNIQUE(pokemon_name, game)
);

CREATE INDEX IF NOT EXISTS version_exclusives_lower_game_idx ON version_exclusives (LOWER(game));
CREATE INDEX IF NOT EXISTS version_exclusives_lower_pair_idx ON version_exclusives (LOWER(game_pair));

CREATE TABLE IF NOT EXISTS trainers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    game           TEXT NOT NULL,
    role           TEXT,
    specialty_type TEXT,
    location       TEXT,
    battle_variant TEXT NOT NULL DEFAULT 'First Battle',
    UNIQUE(name, game, battle_variant)
);

CREATE INDEX IF NOT EXISTS trainers_lower_game_idx ON trainers (LOWER(game));
CREATE INDEX IF NOT EXISTS trainers_lower_role_idx ON trainers (LOWER(role));

CREATE TABLE IF NOT EXISTS trainer_pokemon (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name   TEXT NOT NULL,
    game           TEXT NOT NULL,
    battle_variant TEXT NOT NULL DEFAULT 'First Battle',
    pokemon_name   TEXT NOT NULL,
    level          INTEGER,
    held_item      TEXT,
    ability        TEXT,
    moves          TEXT NOT NULL DEFAULT '[]',   -- JSON array
    team_order     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(trainer_name, game, battle_variant, team_order)
);

CREATE INDEX IF NOT EXISTS trainer_pokemon_lower_trainer_idx ON trainer_pokemon (LOWER(trainer_name));
CREATE INDEX IF NOT EXISTS trainer_pokemon_lower_game_idx    ON trainer_pokemon (LOWER(game));

CREATE TABLE IF NOT EXISTS type_matchups (
    attacking_type TEXT NOT NULL,
    defending_type TEXT NOT NULL,
    multiplier     REAL NOT NULL,
    PRIMARY KEY (attacking_type, defending_type)
);

CREATE INDEX IF NOT EXISTS type_matchups_lower_attacking_idx ON type_matchups (LOWER(attacking_type));
CREATE INDEX IF NOT EXISTS type_matchups_lower_defending_idx ON type_matchups (LOWER(defending_type));

-- ---------------------------------------------------------------------------
-- PokeAPI CSV-sourced tables (pokeapi_csv_loader)
--
-- Identifier-based keys (kebab-case) so queries can match them against API URL
-- slugs without round-tripping through pokemondb's display names.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS move_meta (
    move_identifier TEXT PRIMARY KEY,
    ailment         TEXT,
    ailment_chance  INTEGER,
    flinch_chance   INTEGER,
    crit_rate       INTEGER,
    drain           INTEGER,
    healing         INTEGER,
    stat_chance     INTEGER,
    min_hits        INTEGER,
    max_hits        INTEGER,
    min_turns       INTEGER,
    max_turns       INTEGER,
    category        TEXT
);

CREATE TABLE IF NOT EXISTS move_stat_changes (
    move_identifier TEXT NOT NULL,
    stat            TEXT NOT NULL,
    change          INTEGER NOT NULL,
    PRIMARY KEY (move_identifier, stat)
);

CREATE TABLE IF NOT EXISTS pokemon_past_types (
    pokemon_identifier TEXT NOT NULL,
    generation         INTEGER NOT NULL,
    slot               INTEGER NOT NULL,
    type               TEXT NOT NULL,
    PRIMARY KEY (pokemon_identifier, generation, slot)
);

CREATE TABLE IF NOT EXISTS pokemon_past_abilities (
    pokemon_identifier TEXT NOT NULL,
    generation         INTEGER NOT NULL,
    slot               INTEGER NOT NULL,
    ability            TEXT,
    is_hidden          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (pokemon_identifier, generation, slot)
);

CREATE TABLE IF NOT EXISTS item_names (
    item_identifier TEXT NOT NULL,
    language        TEXT NOT NULL,
    localized_name  TEXT NOT NULL,
    PRIMARY KEY (item_identifier, language)
);

CREATE TABLE IF NOT EXISTS move_names (
    move_identifier TEXT NOT NULL,
    language        TEXT NOT NULL,
    localized_name  TEXT NOT NULL,
    PRIMARY KEY (move_identifier, language)
);

CREATE TABLE IF NOT EXISTS ability_names (
    ability_identifier TEXT NOT NULL,
    language           TEXT NOT NULL,
    localized_name     TEXT NOT NULL,
    PRIMARY KEY (ability_identifier, language)
);

CREATE TABLE IF NOT EXISTS type_names (
    type_identifier TEXT NOT NULL,
    language        TEXT NOT NULL,
    localized_name  TEXT NOT NULL,
    PRIMARY KEY (type_identifier, language)
);

CREATE TABLE IF NOT EXISTS item_attributes (
    item_identifier TEXT NOT NULL,
    attribute       TEXT NOT NULL,
    PRIMARY KEY (item_identifier, attribute)
);

CREATE TABLE IF NOT EXISTS item_extra (
    item_identifier  TEXT PRIMARY KEY,
    fling_power      INTEGER,
    fling_effect     TEXT,
    baby_trigger_for TEXT
);

CREATE TABLE IF NOT EXISTS moves_canonical (
    move_identifier TEXT PRIMARY KEY,
    type            TEXT,
    damage_class    TEXT,
    target          TEXT,
    power           INTEGER,
    accuracy        INTEGER,
    pp              INTEGER,
    priority        INTEGER,
    generation      INTEGER
);

CREATE TABLE IF NOT EXISTS pokemon_moves_vg (
    pokemon_identifier TEXT NOT NULL,
    version_group      TEXT NOT NULL,
    move_identifier    TEXT NOT NULL,
    learn_method       TEXT NOT NULL,
    level              INTEGER,
    move_order         INTEGER,
    PRIMARY KEY (pokemon_identifier, version_group, move_identifier, learn_method)
);

CREATE INDEX IF NOT EXISTS pokemon_moves_vg_pokemon_idx
    ON pokemon_moves_vg (pokemon_identifier, version_group);
-- Supports the LEFT JOIN moves_canonical in db/queries.go MovesByVersionGroup.
CREATE INDEX IF NOT EXISTS pokemon_moves_vg_move_idx
    ON pokemon_moves_vg (move_identifier);
"""


# Every table this schema creates, in creation order. build_db.py asserts the
# live database matches this list exactly.
TABLES = [
    # pokemondb_scraper-sourced (40)
    "pokemon",
    "type_defenses",
    "evolutions",
    "moves",
    "locations",
    "regional_dex",
    "game_national_dex",
    "item_details",
    "move_details",
    "ability_details",
    "ability_pokemon",
    "pokedex_entries",
    "natures",
    "location_encounters",
    "berries",
    "berry_flavors",
    "item_locations",
    "tm_locations",
    "pokemon_names",
    "pokemon_sprites",
    "wild_held_items",
    "pokemon_biology",
    "pokemon_game_locations",
    "raid_events",
    "raid_counters",
    "pokemon_forms",
    "egg_move_parents",
    "pokemon_classification",
    "z_moves",
    "in_game_trades",
    "contest_stats",
    "event_pokemon",
    "mass_outbreaks",
    "pokemon_go",
    "battle_facilities",
    "move_tutor_locations",
    "version_exclusives",
    "trainers",
    "trainer_pokemon",
    "type_matchups",
    # pokeapi_csv_loader-sourced (12)
    "move_meta",
    "move_stat_changes",
    "pokemon_past_types",
    "pokemon_past_abilities",
    "item_names",
    "move_names",
    "ability_names",
    "type_names",
    "item_attributes",
    "item_extra",
    "moves_canonical",
    "pokemon_moves_vg",
]

assert len(TABLES) == 52, f"expected 52 tables, TABLES has {len(TABLES)}"


# Columns that hold a JSON array rather than a scalar. writer.py consults this
# to encode Python lists on the way in, and it is the authoritative list for
# the Go read side's json_each / json.Unmarshal handling.
ARRAY_COLUMNS = {
    "pokemon":             {"types", "abilities", "egg_groups"},
    "evolutions":          {"types"},
    "locations":           {"games", "locations"},
    "regional_dex":        {"types"},
    "location_encounters": {"games"},
    "pokemon_forms":       {"types", "abilities"},
    "move_details":        {"flags"},
    "event_pokemon":       {"moves"},
    "trainer_pokemon":     {"moves"},
}


# Columns stored as 0/1 integers that the source schema declared BOOLEAN.
BOOLEAN_COLUMNS = {
    "ability_pokemon":        {"is_hidden"},
    "pokemon_past_abilities": {"is_hidden"},
    "raid_events":            {"is_active"},
    "pokemon_classification": {
        "is_legendary", "is_mythical", "is_ultra_beast", "is_baby", "is_paradox",
    },
    "pokemon_go": {"shiny_available", "shadow_available"},
}
