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
