import psycopg2
from psycopg2.extras import execute_values
from itemadapter import ItemAdapter

from pokemondb_scraper.items import (
    PokemonItem,
    TypeDefenseItem,
    EvolutionItem,
    MoveItem,
    LocationItem,
    RegionalDexItem,
    GameNationalDexItem,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pokemon (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    url             TEXT,
    national_no     TEXT,
    types           TEXT[],
    species         TEXT,
    height          TEXT,
    weight          TEXT,
    abilities       TEXT[],
    ev_yield        TEXT,
    catch_rate      TEXT,
    base_friendship TEXT,
    base_exp        TEXT,
    growth_rate     TEXT,
    egg_groups      TEXT[],
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

CREATE TABLE IF NOT EXISTS type_defenses (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    type_name    TEXT NOT NULL,
    multiplier   REAL NOT NULL DEFAULT 1.0,
    UNIQUE(pokemon_name, type_name)
);

CREATE TABLE IF NOT EXISTS evolutions (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    number       TEXT,
    evo_name     TEXT NOT NULL,
    evo_url      TEXT,
    types        TEXT[],
    evolves_via  TEXT,
    evolves_from TEXT,
    chain_order  INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS evolutions_unique_entry
    ON evolutions (pokemon_name, evo_name, COALESCE(evolves_from, ''));

CREATE TABLE IF NOT EXISTS moves (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    learn_method TEXT NOT NULL,
    level_or_tm  TEXT,
    move_name    TEXT NOT NULL,
    type         TEXT,
    category     TEXT,
    power        INTEGER,
    accuracy     INTEGER
);

CREATE TABLE IF NOT EXISTS locations (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    games        TEXT[],
    locations    TEXT[]
);

CREATE TABLE IF NOT EXISTS regional_dex (
    id           SERIAL PRIMARY KEY,
    game         TEXT NOT NULL,
    dex_number   INTEGER NOT NULL,
    pokemon_name TEXT NOT NULL,
    types        TEXT[],
    UNIQUE(game, pokemon_name)
);

CREATE TABLE IF NOT EXISTS game_national_dex (
    id           SERIAL PRIMARY KEY,
    game         TEXT NOT NULL,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    national_no  INTEGER NOT NULL,
    UNIQUE(game, pokemon_name)
);
"""


class PostgresPipeline:
    def __init__(self, db_uri):
        self.db_uri = db_uri

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_uri=crawler.settings.get('DATABASE_URI'),
        )

    def open_spider(self, spider):
        self.conn = psycopg2.connect(self.db_uri)
        self.conn.set_client_encoding('UTF8')
        self.cur = self.conn.cursor()
        self.cur.execute(SCHEMA_SQL)
        self.conn.commit()

    def close_spider(self, spider):
        self.conn.commit()
        self.cur.close()
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if isinstance(item, PokemonItem):
            self._upsert_pokemon(adapter)
        elif isinstance(item, TypeDefenseItem):
            self._insert_type_defense(adapter)
        elif isinstance(item, EvolutionItem):
            self._insert_evolution(adapter)
        elif isinstance(item, MoveItem):
            self._insert_move(adapter)
        elif isinstance(item, LocationItem):
            self._insert_location(adapter)
        elif isinstance(item, RegionalDexItem):
            self._upsert_regional_dex(adapter)
        elif isinstance(item, GameNationalDexItem):
            self._upsert_game_national_dex(adapter)

        self.conn.commit()
        return item

    def _upsert_pokemon(self, a):
        self.cur.execute("""
            INSERT INTO pokemon (
                name, url, national_no, types, species, height, weight,
                abilities, ev_yield, catch_rate, base_friendship, base_exp,
                growth_rate, egg_groups, gender_ratio, egg_cycles,
                hp, attack, defense, sp_atk, sp_def, speed, total
            ) VALUES (
                %(name)s, %(url)s, %(national_no)s, %(types)s, %(species)s,
                %(height)s, %(weight)s, %(abilities)s, %(ev_yield)s,
                %(catch_rate)s, %(base_friendship)s, %(base_exp)s,
                %(growth_rate)s, %(egg_groups)s, %(gender_ratio)s,
                %(egg_cycles)s, %(hp)s, %(attack)s, %(defense)s,
                %(sp_atk)s, %(sp_def)s, %(speed)s, %(total)s
            )
            ON CONFLICT (name) DO UPDATE SET
                url = EXCLUDED.url,
                national_no = EXCLUDED.national_no,
                types = EXCLUDED.types,
                species = EXCLUDED.species,
                height = EXCLUDED.height,
                weight = EXCLUDED.weight,
                abilities = EXCLUDED.abilities,
                ev_yield = EXCLUDED.ev_yield,
                catch_rate = EXCLUDED.catch_rate,
                base_friendship = EXCLUDED.base_friendship,
                base_exp = EXCLUDED.base_exp,
                growth_rate = EXCLUDED.growth_rate,
                egg_groups = EXCLUDED.egg_groups,
                gender_ratio = EXCLUDED.gender_ratio,
                egg_cycles = EXCLUDED.egg_cycles,
                hp = EXCLUDED.hp,
                attack = EXCLUDED.attack,
                defense = EXCLUDED.defense,
                sp_atk = EXCLUDED.sp_atk,
                sp_def = EXCLUDED.sp_def,
                speed = EXCLUDED.speed,
                total = EXCLUDED.total
        """, dict(a))

    def _insert_type_defense(self, a):
        self.cur.execute("""
            INSERT INTO type_defenses (pokemon_name, type_name, multiplier)
            VALUES (%(pokemon_name)s, %(type_name)s, %(multiplier)s)
            ON CONFLICT (pokemon_name, type_name) DO UPDATE SET
                multiplier = EXCLUDED.multiplier
        """, dict(a))

    def _insert_evolution(self, a):
        self.cur.execute("""
            INSERT INTO evolutions (pokemon_name, number, evo_name, evo_url, types, evolves_via, evolves_from, chain_order)
            VALUES (%(pokemon_name)s, %(number)s, %(evo_name)s, %(evo_url)s, %(types)s, %(evolves_via)s, %(evolves_from)s, %(chain_order)s)
            ON CONFLICT (pokemon_name, evo_name, COALESCE(evolves_from, '')) DO NOTHING
        """, dict(a))

    def _insert_move(self, a):
        self.cur.execute("""
            INSERT INTO moves (pokemon_name, learn_method, level_or_tm, move_name, type, category, power, accuracy)
            VALUES (%(pokemon_name)s, %(learn_method)s, %(level_or_tm)s, %(move_name)s, %(type)s, %(category)s, %(power)s, %(accuracy)s)
        """, dict(a))

    def _insert_location(self, a):
        self.cur.execute("""
            INSERT INTO locations (pokemon_name, games, locations)
            VALUES (%(pokemon_name)s, %(games)s, %(locations)s)
        """, dict(a))

    def _upsert_regional_dex(self, a):
        self.cur.execute("""
            INSERT INTO regional_dex (game, dex_number, pokemon_name, types)
            VALUES (%(game)s, %(dex_number)s, %(pokemon_name)s, %(types)s)
            ON CONFLICT (game, pokemon_name) DO UPDATE SET
                dex_number = EXCLUDED.dex_number,
                types = EXCLUDED.types
        """, dict(a))

    def _upsert_game_national_dex(self, a):
        self.cur.execute("""
            INSERT INTO game_national_dex (game, pokemon_name, national_no)
            VALUES (%(game)s, %(pokemon_name)s, %(national_no)s)
            ON CONFLICT (game, pokemon_name) DO UPDATE SET
                national_no = EXCLUDED.national_no
        """, dict(a))
