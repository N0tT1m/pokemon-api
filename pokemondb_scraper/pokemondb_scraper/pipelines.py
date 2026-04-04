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
    GameItemDetail,
    MoveDetail,
    AbilityDetail,
    AbilityPokemonItem,
    PokedexEntryItem,
    NatureItem,
    LocationEncounterItem,
    BerryItem,
    BerryFlavorItem,
    ItemLocationItem,
    TmLocationItem,
    PokemonNameItem,
    PokemonSpriteItem,
    WildHeldItemItem,
    PokemonBiologyItem,
    PokemonGameLocationItem,
    RaidEventItem,
    RaidCounterItem,
    PokemonFormItem,
    EggMovePokemonItem,
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

CREATE TABLE IF NOT EXISTS item_details (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT,
    effect      TEXT,
    sprite_url  TEXT,
    buy_price   INTEGER,
    sell_price  INTEGER
);

ALTER TABLE item_details ADD COLUMN IF NOT EXISTS buy_price  INTEGER;
ALTER TABLE item_details ADD COLUMN IF NOT EXISTS sell_price INTEGER;

CREATE TABLE IF NOT EXISTS move_details (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    type          TEXT,
    category      TEXT,
    power         INTEGER,
    accuracy      INTEGER,
    pp            INTEGER,
    effect        TEXT,
    effect_chance INTEGER,
    priority      INTEGER,
    target        TEXT
);

ALTER TABLE move_details ADD COLUMN IF NOT EXISTS priority INTEGER;
ALTER TABLE move_details ADD COLUMN IF NOT EXISTS target   TEXT;

CREATE TABLE IF NOT EXISTS ability_details (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    generation  INTEGER
);

CREATE TABLE IF NOT EXISTS ability_pokemon (
    id            SERIAL PRIMARY KEY,
    ability_name  TEXT NOT NULL REFERENCES ability_details(name) ON DELETE CASCADE,
    pokemon_name  TEXT NOT NULL,
    is_hidden     BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(ability_name, pokemon_name)
);

CREATE TABLE IF NOT EXISTS pokedex_entries (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    game_version TEXT NOT NULL,
    flavor_text  TEXT NOT NULL,
    UNIQUE(pokemon_name, game_version)
);

CREATE TABLE IF NOT EXISTS natures (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    increased_stat  TEXT,
    decreased_stat  TEXT
);

CREATE TABLE IF NOT EXISTS location_encounters (
    id               SERIAL PRIMARY KEY,
    region           TEXT NOT NULL,
    route_name       TEXT NOT NULL,
    pokemon_name     TEXT NOT NULL,
    games            TEXT[],
    encounter_method TEXT,
    rarity           TEXT,
    level_range      TEXT,
    time_of_day      TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS location_encounters_unique ON location_encounters (region, route_name, pokemon_name, COALESCE(encounter_method, ''));

CREATE TABLE IF NOT EXISTS berries (
    id                SERIAL PRIMARY KEY,
    name              TEXT NOT NULL UNIQUE,
    natural_gift_type TEXT,
    natural_gift_power INTEGER,
    size_mm           INTEGER,
    firmness          TEXT,
    effect            TEXT,
    growth_time       INTEGER
);

CREATE TABLE IF NOT EXISTS berry_flavors (
    id          SERIAL PRIMARY KEY,
    berry_name  TEXT NOT NULL REFERENCES berries(name) ON DELETE CASCADE,
    flavor      TEXT NOT NULL,
    potency     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(berry_name, flavor)
);

CREATE TABLE IF NOT EXISTS item_locations (
    id         SERIAL PRIMARY KEY,
    item_name  TEXT NOT NULL,
    game       TEXT NOT NULL,
    location   TEXT NOT NULL,
    method     TEXT,
    UNIQUE(item_name, game, location)
);

CREATE TABLE IF NOT EXISTS tm_locations (
    id         SERIAL PRIMARY KEY,
    tm_number  TEXT NOT NULL,
    move_name  TEXT NOT NULL,
    game       TEXT NOT NULL,
    location   TEXT NOT NULL,
    UNIQUE(tm_number, game, move_name)
);

CREATE TABLE IF NOT EXISTS pokemon_names (
    id             SERIAL PRIMARY KEY,
    pokemon_name   TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    language       TEXT NOT NULL,
    localized_name TEXT NOT NULL,
    UNIQUE(pokemon_name, language)
);

CREATE TABLE IF NOT EXISTS pokemon_sprites (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL REFERENCES pokemon(name) ON DELETE CASCADE,
    sprite_type  TEXT NOT NULL,
    generation   TEXT,
    url          TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pokemon_sprites_unique
    ON pokemon_sprites(pokemon_name, sprite_type, url, COALESCE(generation, ''));

CREATE TABLE IF NOT EXISTS wild_held_items (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    game         TEXT NOT NULL,
    item_name    TEXT NOT NULL,
    rarity       TEXT,
    UNIQUE(pokemon_name, game, item_name)
);

CREATE TABLE IF NOT EXISTS pokemon_biology (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL UNIQUE,
    biology      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pokemon_game_locations (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    game         TEXT NOT NULL,
    location     TEXT NOT NULL,
    method       TEXT,
    UNIQUE(pokemon_name, game, location)
);

CREATE TABLE IF NOT EXISTS raid_events (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    tera_type    TEXT,
    star_rating  INTEGER,
    event_start  TEXT,
    event_end    TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT FALSE,
    source_url   TEXT,
    scraped_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(pokemon_name, COALESCE(tera_type, ''), COALESCE(event_start, ''))
);

CREATE TABLE IF NOT EXISTS raid_counters (
    id              SERIAL PRIMARY KEY,
    pokemon_name    TEXT NOT NULL,
    tera_type       TEXT,
    counter_pokemon TEXT NOT NULL,
    rank            INTEGER,
    notes           TEXT,
    UNIQUE(pokemon_name, COALESCE(tera_type, ''), counter_pokemon)
);

CREATE TABLE IF NOT EXISTS pokemon_forms (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    form_name    TEXT NOT NULL,
    types        TEXT[],
    abilities    TEXT[],
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

CREATE TABLE IF NOT EXISTS egg_move_parents (
    id           SERIAL PRIMARY KEY,
    pokemon_name TEXT NOT NULL,
    move_name    TEXT NOT NULL,
    parent_name  TEXT NOT NULL,
    UNIQUE(pokemon_name, move_name, parent_name)
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
        elif isinstance(item, GameItemDetail):
            self._upsert_item_detail(adapter)
        elif isinstance(item, MoveDetail):
            self._upsert_move_detail(adapter)
        elif isinstance(item, AbilityDetail):
            self._upsert_ability_detail(adapter)
        elif isinstance(item, AbilityPokemonItem):
            self._upsert_ability_pokemon(adapter)
        elif isinstance(item, PokedexEntryItem):
            self._upsert_pokedex_entry(adapter)
        elif isinstance(item, NatureItem):
            self._upsert_nature(adapter)
        elif isinstance(item, LocationEncounterItem):
            self._upsert_location_encounter(adapter)
        elif isinstance(item, BerryItem):
            self._upsert_berry(adapter)
        elif isinstance(item, BerryFlavorItem):
            self._upsert_berry_flavor(adapter)
        elif isinstance(item, ItemLocationItem):
            self._upsert_item_location(adapter)
        elif isinstance(item, TmLocationItem):
            self._upsert_tm_location(adapter)
        elif isinstance(item, PokemonNameItem):
            self._upsert_pokemon_name(adapter)
        elif isinstance(item, PokemonSpriteItem):
            self._upsert_pokemon_sprite(adapter)
        elif isinstance(item, WildHeldItemItem):
            self._upsert_wild_held_item(adapter)
        elif isinstance(item, PokemonBiologyItem):
            self._upsert_pokemon_biology(adapter)
        elif isinstance(item, PokemonGameLocationItem):
            self._upsert_pokemon_game_location(adapter)
        elif isinstance(item, RaidEventItem):
            self._upsert_raid_event(adapter)
        elif isinstance(item, RaidCounterItem):
            self._upsert_raid_counter(adapter)
        elif isinstance(item, PokemonFormItem):
            self._upsert_pokemon_form(adapter)
        elif isinstance(item, EggMovePokemonItem):
            self._upsert_egg_move_parent(adapter)

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

    def _upsert_item_detail(self, a):
        self.cur.execute("""
            INSERT INTO item_details (name, category, effect, sprite_url, buy_price, sell_price)
            VALUES (%(name)s, %(category)s, %(effect)s, %(sprite_url)s, %(buy_price)s, %(sell_price)s)
            ON CONFLICT (name) DO UPDATE SET
                category   = EXCLUDED.category,
                effect     = EXCLUDED.effect,
                sprite_url = EXCLUDED.sprite_url,
                buy_price  = COALESCE(EXCLUDED.buy_price,  item_details.buy_price),
                sell_price = COALESCE(EXCLUDED.sell_price, item_details.sell_price)
        """, dict(a))

    def _upsert_move_detail(self, a):
        self.cur.execute("""
            INSERT INTO move_details (name, type, category, power, accuracy, pp, effect, effect_chance, priority, target)
            VALUES (%(name)s, %(type)s, %(category)s, %(power)s, %(accuracy)s, %(pp)s, %(effect)s, %(effect_chance)s, %(priority)s, %(target)s)
            ON CONFLICT (name) DO UPDATE SET
                type          = EXCLUDED.type,
                category      = EXCLUDED.category,
                power         = EXCLUDED.power,
                accuracy      = EXCLUDED.accuracy,
                pp            = EXCLUDED.pp,
                effect        = EXCLUDED.effect,
                effect_chance = EXCLUDED.effect_chance,
                priority      = COALESCE(EXCLUDED.priority, move_details.priority),
                target        = COALESCE(EXCLUDED.target,   move_details.target)
        """, dict(a))

    def _upsert_ability_detail(self, a):
        self.cur.execute("""
            INSERT INTO ability_details (name, description, generation)
            VALUES (%(name)s, %(description)s, %(generation)s)
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                generation = EXCLUDED.generation
        """, dict(a))

    def _upsert_ability_pokemon(self, a):
        self.cur.execute("""
            INSERT INTO ability_pokemon (ability_name, pokemon_name, is_hidden)
            VALUES (%(ability_name)s, %(pokemon_name)s, %(is_hidden)s)
            ON CONFLICT (ability_name, pokemon_name) DO UPDATE SET
                is_hidden = EXCLUDED.is_hidden
        """, dict(a))

    def _upsert_pokedex_entry(self, a):
        self.cur.execute("""
            INSERT INTO pokedex_entries (pokemon_name, game_version, flavor_text)
            VALUES (%(pokemon_name)s, %(game_version)s, %(flavor_text)s)
            ON CONFLICT (pokemon_name, game_version) DO UPDATE SET
                flavor_text = EXCLUDED.flavor_text
        """, dict(a))

    def _upsert_nature(self, a):
        self.cur.execute("""
            INSERT INTO natures (name, increased_stat, decreased_stat)
            VALUES (%(name)s, %(increased_stat)s, %(decreased_stat)s)
            ON CONFLICT (name) DO UPDATE SET
                increased_stat = EXCLUDED.increased_stat,
                decreased_stat = EXCLUDED.decreased_stat
        """, dict(a))

    def _upsert_location_encounter(self, a):
        self.cur.execute("""
            INSERT INTO location_encounters (region, route_name, pokemon_name, games, encounter_method, rarity, level_range, time_of_day)
            VALUES (%(region)s, %(route_name)s, %(pokemon_name)s, %(games)s, %(encounter_method)s, %(rarity)s, %(level_range)s, %(time_of_day)s)
            ON CONFLICT (region, route_name, pokemon_name, COALESCE(encounter_method, '')) DO UPDATE SET
                games = (
                    SELECT ARRAY(SELECT DISTINCT unnest FROM unnest(location_encounters.games || EXCLUDED.games) ORDER BY 1)
                ),
                rarity = COALESCE(EXCLUDED.rarity, location_encounters.rarity),
                level_range = COALESCE(EXCLUDED.level_range, location_encounters.level_range),
                time_of_day = COALESCE(EXCLUDED.time_of_day, location_encounters.time_of_day)
        """, dict(a))

    def _upsert_berry(self, a):
        self.cur.execute("""
            INSERT INTO berries (name, natural_gift_type, natural_gift_power, size_mm, firmness, effect, growth_time)
            VALUES (%(name)s, %(natural_gift_type)s, %(natural_gift_power)s, %(size_mm)s, %(firmness)s, %(effect)s, %(growth_time)s)
            ON CONFLICT (name) DO UPDATE SET
                natural_gift_type = EXCLUDED.natural_gift_type,
                natural_gift_power = EXCLUDED.natural_gift_power,
                size_mm = EXCLUDED.size_mm,
                firmness = EXCLUDED.firmness,
                effect = EXCLUDED.effect,
                growth_time = EXCLUDED.growth_time
        """, dict(a))

    def _upsert_berry_flavor(self, a):
        self.cur.execute("""
            INSERT INTO berry_flavors (berry_name, flavor, potency)
            VALUES (%(berry_name)s, %(flavor)s, %(potency)s)
            ON CONFLICT (berry_name, flavor) DO UPDATE SET
                potency = EXCLUDED.potency
        """, dict(a))

    def _upsert_item_location(self, a):
        self.cur.execute("""
            INSERT INTO item_locations (item_name, game, location, method)
            VALUES (%(item_name)s, %(game)s, %(location)s, %(method)s)
            ON CONFLICT (item_name, game, location) DO NOTHING
        """, dict(a))

    def _upsert_tm_location(self, a):
        self.cur.execute("""
            INSERT INTO tm_locations (tm_number, move_name, game, location)
            VALUES (%(tm_number)s, %(move_name)s, %(game)s, %(location)s)
            ON CONFLICT (tm_number, game, move_name) DO NOTHING
        """, dict(a))

    def _upsert_pokemon_name(self, a):
        self.cur.execute("""
            INSERT INTO pokemon_names (pokemon_name, language, localized_name)
            VALUES (%(pokemon_name)s, %(language)s, %(localized_name)s)
            ON CONFLICT (pokemon_name, language) DO UPDATE SET
                localized_name = EXCLUDED.localized_name
        """, dict(a))

    def _upsert_pokemon_sprite(self, a):
        self.cur.execute("""
            INSERT INTO pokemon_sprites (pokemon_name, sprite_type, generation, url)
            VALUES (%(pokemon_name)s, %(sprite_type)s, %(generation)s, %(url)s)
            ON CONFLICT (pokemon_name, sprite_type, COALESCE(generation, ''), url) DO NOTHING
        """, dict(a))

    def _upsert_wild_held_item(self, a):
        self.cur.execute("""
            INSERT INTO wild_held_items (pokemon_name, game, item_name, rarity)
            VALUES (%(pokemon_name)s, %(game)s, %(item_name)s, %(rarity)s)
            ON CONFLICT (pokemon_name, game, item_name) DO UPDATE SET
                rarity = EXCLUDED.rarity
        """, dict(a))

    def _upsert_pokemon_biology(self, a):
        self.cur.execute("""
            INSERT INTO pokemon_biology (pokemon_name, biology)
            VALUES (%(pokemon_name)s, %(biology)s)
            ON CONFLICT (pokemon_name) DO UPDATE SET
                biology = EXCLUDED.biology
        """, dict(a))

    def _upsert_pokemon_game_location(self, a):
        self.cur.execute("""
            INSERT INTO pokemon_game_locations (pokemon_name, game, location, method)
            VALUES (%(pokemon_name)s, %(game)s, %(location)s, %(method)s)
            ON CONFLICT (pokemon_name, game, location) DO UPDATE SET
                method = COALESCE(EXCLUDED.method, pokemon_game_locations.method)
        """, dict(a))

    def _upsert_raid_event(self, a):
        self.cur.execute("""
            INSERT INTO raid_events (pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url)
            VALUES (%(pokemon_name)s, %(tera_type)s, %(star_rating)s, %(event_start)s, %(event_end)s, %(is_active)s, %(source_url)s)
            ON CONFLICT (pokemon_name, COALESCE(tera_type, ''), COALESCE(event_start, '')) DO UPDATE SET
                star_rating  = EXCLUDED.star_rating,
                event_end    = EXCLUDED.event_end,
                is_active    = EXCLUDED.is_active,
                source_url   = EXCLUDED.source_url,
                scraped_at   = NOW()
        """, dict(a))

    def _upsert_raid_counter(self, a):
        self.cur.execute("""
            INSERT INTO raid_counters (pokemon_name, tera_type, counter_pokemon, rank, notes)
            VALUES (%(pokemon_name)s, %(tera_type)s, %(counter_pokemon)s, %(rank)s, %(notes)s)
            ON CONFLICT (pokemon_name, COALESCE(tera_type, ''), counter_pokemon) DO UPDATE SET
                rank  = EXCLUDED.rank,
                notes = EXCLUDED.notes
        """, dict(a))

    def _upsert_pokemon_form(self, a):
        self.cur.execute("""
            INSERT INTO pokemon_forms
                (pokemon_name, form_name, types, abilities, height, weight,
                 hp, attack, defense, sp_atk, sp_def, speed, total)
            VALUES
                (%(pokemon_name)s, %(form_name)s, %(types)s, %(abilities)s, %(height)s, %(weight)s,
                 %(hp)s, %(attack)s, %(defense)s, %(sp_atk)s, %(sp_def)s, %(speed)s, %(total)s)
            ON CONFLICT (pokemon_name, form_name) DO UPDATE SET
                types     = EXCLUDED.types,
                abilities = EXCLUDED.abilities,
                height    = EXCLUDED.height,
                weight    = EXCLUDED.weight,
                hp        = EXCLUDED.hp,
                attack    = EXCLUDED.attack,
                defense   = EXCLUDED.defense,
                sp_atk    = EXCLUDED.sp_atk,
                sp_def    = EXCLUDED.sp_def,
                speed     = EXCLUDED.speed,
                total     = EXCLUDED.total
        """, dict(a))

    def _upsert_egg_move_parent(self, a):
        self.cur.execute("""
            INSERT INTO egg_move_parents (pokemon_name, move_name, parent_name)
            VALUES (%(pokemon_name)s, %(move_name)s, %(parent_name)s)
            ON CONFLICT (pokemon_name, move_name, parent_name) DO NOTHING
        """, dict(a))
