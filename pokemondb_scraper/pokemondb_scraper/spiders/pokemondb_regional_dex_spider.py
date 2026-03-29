import re

import scrapy

from pokemondb_scraper.items import RegionalDexItem

# Game slug → display name mapping for all known pokemondb game pages
GAME_PAGES = {
    'red-blue-yellow': 'Red/Blue/Yellow',
    'gold-silver-crystal': 'Gold/Silver/Crystal',
    'ruby-sapphire-emerald': 'Ruby/Sapphire/Emerald',
    'firered-leafgreen': 'FireRed/LeafGreen',
    'diamond-pearl': 'Diamond/Pearl',
    'platinum': 'Platinum',
    'heartgold-soulsilver': 'HeartGold/SoulSilver',
    'black-white': 'Black/White',
    'black-white-2': 'Black 2/White 2',
    'x-y': 'X/Y',
    'omega-ruby-alpha-sapphire': 'Omega Ruby/Alpha Sapphire',
    'sun-moon': 'Sun/Moon',
    'ultra-sun-ultra-moon': 'Ultra Sun/Ultra Moon',
    'lets-go-pikachu-eevee': "Let's Go Pikachu/Eevee",
    'sword-shield': 'Sword/Shield',
    'the-isle-of-armor': 'The Isle of Armor',
    'the-crown-tundra': 'The Crown Tundra',
    'brilliant-diamond-shining-pearl': 'Brilliant Diamond/Shining Pearl',
    'legends-arceus': 'Legends: Arceus',
    'scarlet-violet': 'Scarlet/Violet',
    'the-teal-mask': 'The Teal Mask',
    'the-indigo-disk': 'The Indigo Disk',
    'legends-z-a': 'Legends: Z-A',
}

BASE_URL = 'https://pokemondb.net/pokedex/game/'


class PokemonDbRegionalDex(scrapy.Spider):
    name = "pokemondb_regional_dex"
    allowed_domains = ["pokemondb.net"]

    def start_requests(self):
        for slug, game_name in GAME_PAGES.items():
            yield scrapy.Request(
                url=BASE_URL + slug,
                callback=self.parse_game_dex,
                cb_kwargs={'game': game_name},
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed to fetch: {failure.request.url}")

    def parse_game_dex(self, response, game):
        # pokemondb game pages use infocard divs in a grid
        for card in response.xpath('//div[has-class("infocard")]'):
            name = card.xpath('.//a[has-class("ent-name")]/text()').get('').strip()
            if not name:
                continue

            # Dex number is in a small tag, e.g. "#001"
            number_text = card.xpath('.//small[1]/text()').get('').strip()
            dex_number = None
            match = re.search(r'#?(\d+)', number_text)
            if match:
                dex_number = int(match.group(1))

            types = card.xpath('.//small[2]//a/text()').getall()

            yield RegionalDexItem(
                game=game,
                dex_number=dex_number,
                pokemon_name=name,
                types=[t.strip() for t in types],
            )
