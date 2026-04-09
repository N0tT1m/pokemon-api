import re
import scrapy
from pokemondb_scraper.items import BattleFacilityItem

# Known battle facilities per game — pokemondb has pages for these
# Structured as (slug, display_name, game, region, facility_type, currency)
BATTLE_FACILITIES = [
    # Gen 1
    ('red-blue', 'Red/Blue', 'Kanto', None, None),
    # Gen 2
    ('gold-silver', 'Gold/Silver', 'Johto', None, None),
    # Gen 3
    ('ruby-sapphire', 'Ruby/Sapphire', 'Hoenn', None, None),
    ('emerald', 'Emerald', 'Hoenn', None, None),
    ('firered-leafgreen', 'FireRed/LeafGreen', 'Kanto', None, None),
    # Gen 4
    ('diamond-pearl', 'Diamond/Pearl', 'Sinnoh', None, None),
    ('platinum', 'Platinum', 'Sinnoh', None, None),
    ('heartgold-soulsilver', 'HeartGold/SoulSilver', 'Johto', None, None),
    # Gen 5
    ('black-white', 'Black/White', 'Unova', None, None),
    ('black-white-2', 'Black 2/White 2', 'Unova', None, None),
    # Gen 6
    ('x-y', 'X/Y', 'Kalos', None, None),
    ('omega-ruby-alpha-sapphire', 'Omega Ruby/Alpha Sapphire', 'Hoenn', None, None),
    # Gen 7
    ('sun-moon', 'Sun/Moon', 'Alola', None, None),
    ('ultra-sun-ultra-moon', 'Ultra Sun/Ultra Moon', 'Alola', None, None),
    # Gen 8
    ('sword-shield', 'Sword/Shield', 'Galar', None, None),
    ('brilliant-diamond-shining-pearl', 'Brilliant Diamond/Shining Pearl', 'Sinnoh', None, None),
    # Gen 9
    ('scarlet-violet', 'Scarlet/Violet', 'Paldea', None, None),
]

# Known battle facility names and their types
FACILITY_TYPES = {
    'battle tower': ('Battle Tower', 'BP'),
    'battle frontier': ('Battle Frontier', 'BP'),
    'battle factory': ('Battle Factory', 'BP'),
    'battle pike': ('Battle Pike', 'BP'),
    'battle arena': ('Battle Arena', 'BP'),
    'battle palace': ('Battle Palace', 'BP'),
    'battle dome': ('Battle Dome', 'BP'),
    'battle pyramid': ('Battle Pyramid', 'BP'),
    'battle maison': ('Battle Maison', 'BP'),
    'battle institute': ('Battle Institute', 'BP'),
    'battle tree': ('Battle Tree', 'BP'),
    'battle royal': ('Battle Royal Dome', 'None'),
    'battle stadium': ('Battle Stadium', 'None'),
    'academy ace tournament': ('Academy Ace Tournament', 'None'),
    'porto marinada': ('Porto Marinada Auction', 'Coins'),
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _identify_facility(text):
    """Return (facility_type, currency) if text matches a known facility."""
    lower = text.lower()
    for key, (ftype, currency) in FACILITY_TYPES.items():
        if key in lower:
            return ftype, currency
    return None, None


class PokemonDbBattleFacilitiesSpider(scrapy.Spider):
    """
    Scrapes battle facility metadata from pokemondb.net game-specific pages.

    Yields BattleFacilityItem for each post-game battle facility found,
    including: name, game, region, facility type, description, and currency.
    """

    name = "pokemondb_battle_facilities"
    allowed_domains = ["pokemondb.net"]

    def start_requests(self):
        for slug, game, region, _, _ in BATTLE_FACILITIES:
            url = f'https://pokemondb.net/{slug}'
            yield scrapy.Request(
                url,
                callback=self.parse_game_page,
                cb_kwargs={'game': game, 'region': region},
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.url}")

    def parse_game_page(self, response, game, region):
        """
        Game index pages on pokemondb link to facility-specific pages.
        Look for links containing battle facility keywords.
        """
        for link in response.css('a[href]'):
            href = link.attrib.get('href', '')
            text = _clean(' '.join(link.css('::text').getall()))
            facility_type, currency = _identify_facility(text)
            if facility_type:
                yield response.follow(
                    href,
                    callback=self.parse_facility_page,
                    cb_kwargs={
                        'game': game,
                        'region': region,
                        'facility_name': text,
                        'facility_type': facility_type,
                        'currency': currency,
                    },
                    errback=self.handle_error,
                )

    def parse_facility_page(self, response, game, region, facility_name, facility_type, currency):
        """Parse an individual battle facility page."""
        # Get a brief description from the first paragraph
        description = None
        for p in response.css('main p, article p'):
            text = _clean(' '.join(p.css('::text').getall()))
            if text and len(text) > 30:
                description = text
                break

        yield BattleFacilityItem(
            name=facility_name,
            game=game,
            region=region,
            facility_type=facility_type,
            description=description,
            currency=currency,
        )

        # Also check for additional facilities linked from this page
        for link in response.css('a[href]'):
            href = link.attrib.get('href', '')
            text = _clean(' '.join(link.css('::text').getall()))
            ft, cur = _identify_facility(text)
            if ft and ft != facility_type:
                yield response.follow(
                    href,
                    callback=self.parse_facility_page,
                    cb_kwargs={
                        'game': game,
                        'region': region,
                        'facility_name': text,
                        'facility_type': ft,
                        'currency': cur,
                    },
                    errback=self.handle_error,
                )
