import re
import scrapy
from pokemondb_scraper.items import VersionExclusiveItem

# Bulbapedia version exclusive pages — one per game pair
VERSION_EXCLUSIVE_PAGES = {
    'Red/Blue':                    'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_I)',
    'Gold/Silver':                 'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_II)',
    'Ruby/Sapphire':               'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_III)',
    'Diamond/Pearl':               'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_IV)',
    'Black/White':                 'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_V)',
    'X/Y':                         'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_VI)',
    'Sun/Moon':                    'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_VII)',
    'Sword/Shield':                'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_VIII)',
    'Scarlet/Violet':              'https://bulbapedia.bulbagarden.net/wiki/Version-exclusive_Pok%C3%A9mon_(Generation_IX)',
}

# For paired games, map section headings to individual version names
PAIR_MAP = {
    'Red/Blue':          ('Red',          'Blue'),
    'Gold/Silver':       ('Gold',         'Silver'),
    'Ruby/Sapphire':     ('Ruby',         'Sapphire'),
    'Diamond/Pearl':     ('Diamond',      'Pearl'),
    'Black/White':       ('Black',        'White'),
    'X/Y':               ('X',            'Y'),
    'Sun/Moon':          ('Sun',          'Moon'),
    'Sword/Shield':      ('Sword',        'Shield'),
    'Scarlet/Violet':    ('Scarlet',      'Violet'),
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


class BulbapediaVersionExclusivesSpider(scrapy.Spider):
    """
    Scrapes version-exclusive Pokemon per game pair from Bulbapedia.

    Yields VersionExclusiveItem for each Pokemon that is exclusive to one
    version of a game pair (e.g., Scyther in Red but not Blue).
    """

    name = "bulbapedia_version_exclusives"
    allowed_domains = ["bulbapedia.bulbagarden.net"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
    }

    def start_requests(self):
        for game_pair, url in VERSION_EXCLUSIVE_PAGES.items():
            yield scrapy.Request(
                url,
                callback=self.parse_exclusives_page,
                cb_kwargs={'game_pair': game_pair},
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.url}")

    def parse_exclusives_page(self, response, game_pair):
        """
        Bulbapedia version exclusive pages have two-column tables or two separate
        sections — one per version. Each column/section lists Pokemon by name.
        """
        ver_a, ver_b = PAIR_MAP.get(game_pair, (game_pair + ' A', game_pair + ' B'))

        current_version = None

        for el in response.xpath('//h2 | //h3 | //h4 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag in ('h2', 'h3', 'h4'):
                # Identify which version this section is for
                lower = text.lower()
                if ver_a.lower() in lower:
                    current_version = ver_a
                elif ver_b.lower() in lower:
                    current_version = ver_b
                # Reset if it's a generic section
                elif any(kw in lower for kw in ('exclusive', 'only in', 'version')):
                    current_version = None

            elif tag == 'table':
                yield from self._parse_exclusives_table(el, game_pair, ver_a, ver_b, current_version)

    def _parse_exclusives_table(self, table, game_pair, ver_a, ver_b, current_version):
        """
        Parse a table of version exclusives.

        Tables may have two columns (one per version) or be single-version lists.
        """
        headers = [_clean(th) for th in table.css('th ::text').getall()]
        lower_headers = [h.lower() for h in headers]

        # Two-column table: find column for each version
        col_a = next(
            (i for i, h in enumerate(lower_headers) if ver_a.lower() in h), None
        )
        col_b = next(
            (i for i, h in enumerate(lower_headers) if ver_b.lower() in h), None
        )

        if col_a is not None and col_b is not None:
            # Two-column layout
            for row in table.css('tr'):
                cells = row.css('td')
                if not cells:
                    continue
                if col_a < len(cells):
                    name_a = _clean(cells[col_a].css('a::text, ::text').get(''))
                    name_a = re.sub(r'\s*\(.*?\)', '', name_a).strip()
                    if name_a and name_a.lower() not in ('—', '-', ''):
                        yield VersionExclusiveItem(
                            pokemon_name=name_a,
                            game=ver_a,
                            game_pair=game_pair,
                        )
                if col_b < len(cells):
                    name_b = _clean(cells[col_b].css('a::text, ::text').get(''))
                    name_b = re.sub(r'\s*\(.*?\)', '', name_b).strip()
                    if name_b and name_b.lower() not in ('—', '-', ''):
                        yield VersionExclusiveItem(
                            pokemon_name=name_b,
                            game=ver_b,
                            game_pair=game_pair,
                        )
        elif current_version:
            # Single-version table
            for row in table.css('tr'):
                cells = row.css('td')
                if not cells:
                    continue
                name = _clean(cells[0].css('a::text, ::text').get(''))
                name = re.sub(r'\s*\(.*?\)', '', name).strip()
                if name and name.lower() not in ('—', '-', ''):
                    yield VersionExclusiveItem(
                        pokemon_name=name,
                        game=current_version,
                        game_pair=game_pair,
                    )
