import scrapy


class PokemonItem(scrapy.Item):
    """Core Pokemon data from the vitals tables."""
    name = scrapy.Field()
    url = scrapy.Field()
    # Pokedex data
    national_no = scrapy.Field()
    types = scrapy.Field()           # list of strings
    species = scrapy.Field()
    height = scrapy.Field()
    weight = scrapy.Field()
    abilities = scrapy.Field()       # list of strings
    # Training
    ev_yield = scrapy.Field()
    catch_rate = scrapy.Field()
    base_friendship = scrapy.Field()
    base_exp = scrapy.Field()
    growth_rate = scrapy.Field()
    # Breeding
    egg_groups = scrapy.Field()      # list of strings
    gender_ratio = scrapy.Field()
    egg_cycles = scrapy.Field()
    # Base stats
    hp = scrapy.Field()
    attack = scrapy.Field()
    defense = scrapy.Field()
    sp_atk = scrapy.Field()
    sp_def = scrapy.Field()
    speed = scrapy.Field()
    total = scrapy.Field()


class TypeDefenseItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    type_name = scrapy.Field()
    multiplier = scrapy.Field()      # float: 0, 0.25, 0.5, 1, 2, 4


class EvolutionItem(scrapy.Item):
    pokemon_name = scrapy.Field()    # the Pokemon page this was scraped from
    number = scrapy.Field()
    evo_name = scrapy.Field()
    evo_url = scrapy.Field()
    types = scrapy.Field()           # list of strings
    evolves_via = scrapy.Field()     # e.g. "use Tart Apple", or None for base form
    evolves_from = scrapy.Field()    # name of the Pokemon this evolves from, or None for base
    chain_order = scrapy.Field()     # position in the chain (0-based)


class MoveItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    learn_method = scrapy.Field()    # "level-up" or "tm"
    level_or_tm = scrapy.Field()     # level number or TM name
    move_name = scrapy.Field()
    type = scrapy.Field()
    category = scrapy.Field()        # Physical, Special, Status
    power = scrapy.Field()           # int or None
    accuracy = scrapy.Field()        # int or None


class LocationItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    games = scrapy.Field()           # list of strings
    locations = scrapy.Field()       # list of strings


class RegionalDexItem(scrapy.Item):
    """A Pokemon's entry in a game-specific regional dex."""
    game = scrapy.Field()            # e.g. "Brilliant Diamond/Shining Pearl"
    dex_number = scrapy.Field()      # regional dex number (int)
    pokemon_name = scrapy.Field()
    types = scrapy.Field()           # list of strings


class GameNationalDexItem(scrapy.Item):
    """A Pokemon's presence in a game's national dex (derived from Local № data)."""
    game = scrapy.Field()            # e.g. "Brilliant Diamond/Shining Pearl"
    pokemon_name = scrapy.Field()
    national_no = scrapy.Field()     # int — the universal national dex number


class GameItemDetail(scrapy.Item):
    name = scrapy.Field()
    category = scrapy.Field()
    effect = scrapy.Field()
    sprite_url = scrapy.Field()
    buy_price = scrapy.Field()   # int, Pokémon Dollars — None if not purchasable
    sell_price = scrapy.Field()  # int, Pokémon Dollars — None if not sellable

class MoveDetail(scrapy.Item):
    name = scrapy.Field()
    type = scrapy.Field()
    category = scrapy.Field()
    power = scrapy.Field()
    accuracy = scrapy.Field()
    pp = scrapy.Field()
    effect = scrapy.Field()
    effect_chance = scrapy.Field()
    priority = scrapy.Field()            # int, e.g. 0, +1, -6
    target = scrapy.Field()              # text, e.g. "Selected Pokémon"
    generation_introduced = scrapy.Field()  # int, e.g. 1
    z_move_equivalent = scrapy.Field()   # name of Z-Move this becomes, or None
    max_move_equivalent = scrapy.Field() # name of Max Move this becomes, or None
    contest_type = scrapy.Field()        # e.g. "Cool", "Cute", or None
    flags = scrapy.Field()               # list of strings, e.g. ["Contact", "Protect"]

class AbilityDetail(scrapy.Item):
    name = scrapy.Field()
    description = scrapy.Field()
    generation = scrapy.Field()

class AbilityPokemonItem(scrapy.Item):
    ability_name = scrapy.Field()
    pokemon_name = scrapy.Field()
    is_hidden = scrapy.Field()

class PokedexEntryItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    game_version = scrapy.Field()
    flavor_text = scrapy.Field()

class NatureItem(scrapy.Item):
    name = scrapy.Field()
    increased_stat = scrapy.Field()
    decreased_stat = scrapy.Field()

class LocationEncounterItem(scrapy.Item):
    region = scrapy.Field()
    route_name = scrapy.Field()
    pokemon_name = scrapy.Field()
    games = scrapy.Field()
    encounter_method = scrapy.Field()
    rarity = scrapy.Field()
    level_range = scrapy.Field()
    time_of_day = scrapy.Field()

class BerryItem(scrapy.Item):
    name = scrapy.Field()
    natural_gift_type = scrapy.Field()
    natural_gift_power = scrapy.Field()
    size_mm = scrapy.Field()
    firmness = scrapy.Field()
    effect = scrapy.Field()
    growth_time = scrapy.Field()

class BerryFlavorItem(scrapy.Item):
    berry_name = scrapy.Field()
    flavor = scrapy.Field()
    potency = scrapy.Field()

class ItemLocationItem(scrapy.Item):
    item_name = scrapy.Field()
    game = scrapy.Field()
    location = scrapy.Field()
    method = scrapy.Field()

class TmLocationItem(scrapy.Item):
    tm_number = scrapy.Field()
    move_name = scrapy.Field()
    game = scrapy.Field()
    location = scrapy.Field()

class PokemonNameItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    language = scrapy.Field()
    localized_name = scrapy.Field()

class PokemonSpriteItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    sprite_type = scrapy.Field()
    generation = scrapy.Field()
    url = scrapy.Field()

class WildHeldItemItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    game = scrapy.Field()
    item_name = scrapy.Field()
    rarity = scrapy.Field()

class PokemonBiologyItem(scrapy.Item):
    pokemon_name = scrapy.Field()
    biology = scrapy.Field()

class PokemonGameLocationItem(scrapy.Item):
    """How/where to find a Pokemon in each game, including special methods."""
    pokemon_name = scrapy.Field()   # e.g. "Spiritomb"
    game         = scrapy.Field()   # e.g. "Diamond/Pearl"
    location     = scrapy.Field()   # e.g. "Hallowed Tower (32 underground encounters)"
    method       = scrapy.Field()   # e.g. "Special", "Wild", "Gift", "Fossil", "Trade", "Event"


class PokemonFormItem(scrapy.Item):
    """Stats/types/abilities for a non-base form (Mega, regional variant, etc.)."""
    pokemon_name = scrapy.Field()   # base Pokemon name, e.g. "Rotom"
    form_name    = scrapy.Field()   # form label, e.g. "Heat Rotom"
    types        = scrapy.Field()   # list of strings
    abilities    = scrapy.Field()   # list of strings
    height       = scrapy.Field()   # text
    weight       = scrapy.Field()   # text
    hp           = scrapy.Field()
    attack       = scrapy.Field()
    defense      = scrapy.Field()
    sp_atk       = scrapy.Field()
    sp_def       = scrapy.Field()
    speed        = scrapy.Field()
    total        = scrapy.Field()


class EggMovePokemonItem(scrapy.Item):
    """A parent Pokemon that can pass a given egg move."""
    pokemon_name = scrapy.Field()   # the Pokemon that learns the egg move
    move_name    = scrapy.Field()   # the egg move
    parent_name  = scrapy.Field()   # a compatible parent


class RaidEventItem(scrapy.Item):
    """A Tera Raid event scraped from game8.co."""
    pokemon_name = scrapy.Field()   # e.g. "Charizard"
    tera_type    = scrapy.Field()   # e.g. "Dragon"
    star_rating  = scrapy.Field()   # int, e.g. 7
    event_start  = scrapy.Field()   # text date string
    event_end    = scrapy.Field()   # text date string
    is_active    = scrapy.Field()   # bool
    source_url   = scrapy.Field()   # game8 article URL


class RaidCounterItem(scrapy.Item):
    """A recommended counter Pokemon for a Tera Raid event."""
    pokemon_name    = scrapy.Field()   # raid Pokemon, e.g. "Charizard"
    tera_type       = scrapy.Field()   # tera type of the raid
    counter_pokemon = scrapy.Field()   # recommended counter, e.g. "Azumarill"
    rank            = scrapy.Field()   # int, position in the recommended list
    notes           = scrapy.Field()   # optional notes/reason


class PokemonClassificationItem(scrapy.Item):
    """Classification metadata not available from the main pokemondb spider."""
    pokemon_name         = scrapy.Field()
    generation_introduced = scrapy.Field()  # int, 1-9
    is_legendary         = scrapy.Field()   # bool
    is_mythical          = scrapy.Field()   # bool
    is_ultra_beast       = scrapy.Field()   # bool
    is_baby              = scrapy.Field()   # bool
    is_paradox           = scrapy.Field()   # bool
    color                = scrapy.Field()   # e.g. "Red", "Blue"
    shape                = scrapy.Field()   # e.g. "Humanoid", "Quadruped"
    habitat              = scrapy.Field()   # e.g. "Forest", "Mountain", "Sea"


class ZMoveItem(scrapy.Item):
    """A Z-Move and its associated base move."""
    name       = scrapy.Field()   # e.g. "Inferno Overdrive"
    type       = scrapy.Field()   # e.g. "Fire"
    power      = scrapy.Field()   # int or None (status Z-Moves have no power)
    effect     = scrapy.Field()   # description text
    base_move  = scrapy.Field()   # the normal move it upgrades from, e.g. "Flamethrower"
    category   = scrapy.Field()   # Physical, Special, Status


class InGameTradeItem(scrapy.Item):
    """An in-game NPC trade within a Pokemon game."""
    game              = scrapy.Field()   # e.g. "Red/Blue"
    location          = scrapy.Field()   # e.g. "Cerulean City"
    offered_pokemon   = scrapy.Field()   # what the player receives
    offered_level     = scrapy.Field()   # int or None
    offered_item      = scrapy.Field()   # held item on received Pokemon, or None
    requested_pokemon = scrapy.Field()   # what the player must give
    npc_name          = scrapy.Field()   # NPC who makes the offer
    notes             = scrapy.Field()   # any special conditions


class ContestStatItem(scrapy.Item):
    """A Pokemon's contest condition stats for a specific contest type."""
    pokemon_name  = scrapy.Field()   # e.g. "Bulbasaur"
    contest_type  = scrapy.Field()   # "Cool", "Beautiful", "Cute", "Tough", "Smart"
    appeal        = scrapy.Field()   # int
    jam           = scrapy.Field()   # int


class EventPokemonItem(scrapy.Item):
    """A historical event/distribution Pokemon."""
    name                = scrapy.Field()   # Pokemon name
    game                = scrapy.Field()   # game(s) it was distributed for
    year                = scrapy.Field()   # int, distribution year
    level               = scrapy.Field()   # int
    held_item           = scrapy.Field()   # item it holds
    moves               = scrapy.Field()   # list of move strings
    ot_name             = scrapy.Field()   # OT name (e.g. "GF", "Movie14")
    distribution_method = scrapy.Field()   # e.g. "Wi-Fi", "Serial Code", "Local Wireless"
    notes               = scrapy.Field()   # additional notes


class MassOutbreakItem(scrapy.Item):
    """A mass outbreak spawn for Legends: Arceus or Scarlet/Violet."""
    game         = scrapy.Field()   # e.g. "Legends: Arceus", "Scarlet/Violet"
    region       = scrapy.Field()   # e.g. "Obsidian Fieldlands"
    location     = scrapy.Field()   # e.g. "Aspiration Hill"
    pokemon_name = scrapy.Field()   # e.g. "Bidoof"
    notes        = scrapy.Field()   # any special conditions (alpha, etc.)


class PokemonGoItem(scrapy.Item):
    """Pokemon GO specific stats for a Pokemon."""
    pokemon_name      = scrapy.Field()   # e.g. "Bulbasaur"
    max_cp            = scrapy.Field()   # int
    buddy_distance_km = scrapy.Field()   # int, 1/3/5/10/20
    base_attack       = scrapy.Field()   # int, GO-specific base stat
    base_defense      = scrapy.Field()   # int, GO-specific base stat
    base_stamina      = scrapy.Field()   # int, GO-specific base stat (HP)
    shiny_available   = scrapy.Field()   # bool
    shadow_available  = scrapy.Field()   # bool


class BattleFacilityItem(scrapy.Item):
    """A post-game battle facility."""
    name          = scrapy.Field()   # e.g. "Battle Tower"
    game          = scrapy.Field()   # e.g. "Sword/Shield"
    region        = scrapy.Field()   # e.g. "Galar"
    facility_type = scrapy.Field()   # e.g. "Battle Tower", "Battle Frontier"
    description   = scrapy.Field()   # brief description of the facility
    currency      = scrapy.Field()   # reward currency, e.g. "BP"


class MoveTutorLocationItem(scrapy.Item):
    """A move tutor NPC that teaches a specific move in a specific game."""
    move_name = scrapy.Field()   # e.g. "Draco Meteor"
    game      = scrapy.Field()   # e.g. "Diamond/Pearl"
    location  = scrapy.Field()   # e.g. "Pastoria City"
    cost      = scrapy.Field()   # e.g. "4 Blue Shards", "Free", "40 BP"


class VersionExclusiveItem(scrapy.Item):
    """A Pokemon that is exclusive to one version of a game pair."""
    pokemon_name = scrapy.Field()   # e.g. "Scyther"
    game         = scrapy.Field()   # the full game title, e.g. "FireRed"
    game_pair    = scrapy.Field()   # the paired titles, e.g. "FireRed/LeafGreen"


class TrainerItem(scrapy.Item):
    """A named trainer (gym leader, elite four member, champion, etc.)."""
    name            = scrapy.Field()   # e.g. "Brock"
    game            = scrapy.Field()   # e.g. "Red/Blue"
    role            = scrapy.Field()   # e.g. "Gym Leader", "Elite Four", "Champion", "Team Star Boss"
    specialty_type  = scrapy.Field()   # e.g. "Rock" — None for champions with no specialty
    location        = scrapy.Field()   # e.g. "Pewter City Gym"
    battle_variant  = scrapy.Field()   # e.g. "First Battle", "Rematch", "Champion Round 2"


class TrainerPokemonItem(scrapy.Item):
    """A Pokemon on a specific trainer's team."""
    trainer_name    = scrapy.Field()   # e.g. "Brock"
    game            = scrapy.Field()   # e.g. "Red/Blue"
    battle_variant  = scrapy.Field()   # e.g. "First Battle", "Rematch"
    pokemon_name    = scrapy.Field()   # e.g. "Geodude"
    level           = scrapy.Field()   # int, e.g. 12
    held_item       = scrapy.Field()   # e.g. "Sitrus Berry" — None if not applicable
    ability         = scrapy.Field()   # e.g. "Sturdy" — None if not applicable
    moves           = scrapy.Field()   # list of move name strings
    team_order      = scrapy.Field()   # int, position in team (0-based)
