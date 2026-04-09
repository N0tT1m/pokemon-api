import re
import scrapy
from pokemondb_scraper.items import PokemonClassificationItem

# National dex number → generation mapping
GEN_RANGES = [
    (1,   151,  1),
    (152, 251,  2),
    (252, 386,  3),
    (387, 493,  4),
    (494, 649,  5),
    (650, 721,  6),
    (722, 809,  7),
    (810, 905,  8),
    (906, 9999, 9),
]


def national_no_to_gen(national_no):
    if not national_no:
        return None
    try:
        n = int(str(national_no).strip().lstrip('#'))
    except (ValueError, AttributeError):
        return None
    for lo, hi, gen in GEN_RANGES:
        if lo <= n <= hi:
            return gen
    return None


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


# Category pages that enumerate Pokemon by classification
CATEGORY_PAGES = {
    'legendary':   'https://bulbapedia.bulbagarden.net/wiki/Legendary_Pok%C3%A9mon',
    'mythical':    'https://bulbapedia.bulbagarden.net/wiki/Mythical_Pok%C3%A9mon',
    'ultra_beast': 'https://bulbapedia.bulbagarden.net/wiki/Ultra_Beast',
    'baby':        'https://bulbapedia.bulbagarden.net/wiki/Baby_Pok%C3%A9mon',
    'paradox':     'https://bulbapedia.bulbagarden.net/wiki/Paradox_Pok%C3%A9mon',
}

# Color and shape values Bulbapedia uses
KNOWN_COLORS = {'Red', 'Blue', 'Yellow', 'Green', 'Black', 'Brown', 'Purple', 'Gray', 'White', 'Pink'}
KNOWN_SHAPES = {
    'Head only', 'Serpentine', 'Finned', 'Bipedal, tailed', 'Bipedal, tailless',
    'Quadruped', 'Multi-winged', 'Multi-limbed', 'Two pairs of legs', 'Winged',
    'Several legs', 'Humanoid', 'Multiped', 'Several bodies',
}


class BulbapediaClassificationSpider(scrapy.Spider):
    """
    Scrapes Pokemon classification metadata from Bulbapedia:
      - Legendary / Mythical / Ultra Beast / Baby / Paradox status (from category pages)
      - Color, shape, habitat, generation (from individual Pokemon pages)
    """

    name = "bulbapedia_classification"
    allowed_domains = ["bulbapedia.bulbagarden.net"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track classification flags per Pokemon
        self._flags = {}   # pokemon_name → dict of bools
        self._seen_pokemon = set()  # already-visited individual pages

    def start_requests(self):
        for classification, url in CATEGORY_PAGES.items():
            yield scrapy.Request(
                url,
                callback=self.parse_category_page,
                cb_kwargs={'classification': classification},
            )

    def parse_category_page(self, response, classification):
        """Extract Pokemon names from a Bulbapedia classification page."""
        # Pokemon are listed in tables or as links within the article body
        seen = set()
        for link in response.css('table a[href*="/wiki/"]'):
            name = _clean(link.css('::text').get(''))
            href = link.attrib.get('href', '')
            # Skip navigation links and meta pages
            if not name or ':' in href or name.startswith('List of'):
                continue
            if '(' in name or name in ('Pokémon', 'Pokemon'):
                continue
            # Filter to likely Pokemon names (capitalized, no spaces in most cases)
            if not name[0].isupper():
                continue
            if name in seen:
                continue
            seen.add(name)

            if name not in self._flags:
                self._flags[name] = {
                    'is_legendary': False,
                    'is_mythical': False,
                    'is_ultra_beast': False,
                    'is_baby': False,
                    'is_paradox': False,
                }
            self._flags[name][f'is_{classification}'] = True

            # Visit individual page for color/shape/habitat/generation if not seen yet
            if name not in self._seen_pokemon:
                self._seen_pokemon.add(name)
                yield response.follow(
                    href,
                    callback=self.parse_pokemon_page,
                    cb_kwargs={'pokemon_name': name},
                    errback=self.handle_error,
                )

        # Yield classification items for all identified Pokemon
        for pokemon_name, flags in self._flags.items():
            yield PokemonClassificationItem(
                pokemon_name=pokemon_name,
                generation_introduced=None,  # filled by individual page visit
                color=None,
                shape=None,
                habitat=None,
                **flags,
            )

    def parse_pokemon_page(self, response, pokemon_name):
        """Extract color, shape, habitat, and generation from a Bulbapedia Pokemon page."""
        vitals = {}
        for row in response.css('table.roundy tr, table.wikitable tr'):
            th = _clean(' '.join(row.css('th ::text, th::text').getall()))
            td = _clean(' '.join(row.css('td ::text, td::text').getall()))
            if th and td:
                vitals[th.lower()] = td

        color = None
        for key, val in vitals.items():
            if 'color' in key:
                for c in KNOWN_COLORS:
                    if c.lower() in val.lower():
                        color = c
                        break

        shape = None
        for key, val in vitals.items():
            if 'body style' in key or 'shape' in key:
                shape = val.strip() or None

        habitat = None
        for key, val in vitals.items():
            if 'habitat' in key:
                habitat = val.strip() or None

        # National dex number for generation derivation
        national_no = None
        for key, val in vitals.items():
            if 'national' in key or 'ndex' in key:
                m = re.search(r'(\d+)', val)
                if m:
                    national_no = int(m.group(1))
                break
        generation_introduced = national_no_to_gen(national_no)

        flags = self._flags.get(pokemon_name, {
            'is_legendary': False,
            'is_mythical': False,
            'is_ultra_beast': False,
            'is_baby': False,
            'is_paradox': False,
        })

        yield PokemonClassificationItem(
            pokemon_name=pokemon_name,
            generation_introduced=generation_introduced,
            color=color,
            shape=shape,
            habitat=habitat,
            **flags,
        )

    def handle_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.url}")
