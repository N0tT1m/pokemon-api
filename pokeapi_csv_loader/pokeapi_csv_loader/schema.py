"""Schema additions for PokeAPI CSV-sourced data.

These tables are entirely additive to the pokemondb_scraper schema. They use
identifier-based keys (kebab-case) so queries can match them against API URL
slugs without round-tripping through pokemondb's display names.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS move_meta (
    move_identifier  TEXT PRIMARY KEY,
    ailment          TEXT,
    ailment_chance   INTEGER,
    flinch_chance    INTEGER,
    crit_rate        INTEGER,
    drain            INTEGER,
    healing          INTEGER,
    stat_chance      INTEGER,
    min_hits         INTEGER,
    max_hits         INTEGER,
    min_turns        INTEGER,
    max_turns        INTEGER,
    category         TEXT
);

CREATE TABLE IF NOT EXISTS move_stat_changes (
    move_identifier  TEXT NOT NULL,
    stat             TEXT NOT NULL,
    change           INTEGER NOT NULL,
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
    is_hidden          BOOLEAN NOT NULL DEFAULT FALSE,
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
"""
