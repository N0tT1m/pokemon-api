import re
import scrapy
from pokemondb_scraper.items import MassOutbreakItem

START_URLS = [
    # Legends: Arceus mass outbreaks
    'https://bulbapedia.bulbagarden.net/wiki/Mass_outbreak',
    # Scarlet/Violet mass outbreaks
    'https://bulbapedia.bulbagarden.net/wiki/Mass_Outbreak_(Scarlet_and_Violet)',
]

GAME_MAP = {
    'arceus': 'Legends: Arceus',
    'legends: arceus': 'Legends: Arceus',
    'scarlet': 'Scarlet/Violet',
    'violet': 'Scarlet/Violet',
    'scarlet/violet': 'Scarlet/Violet',
    'scarlet and violet': 'Scarlet/Violet',
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _infer_game(url, text=''):
    """Infer which game the outbreak page relates to."""
    combined = (url + ' ' + text).lower()
    if 'arceus' in combined:
        return 'Legends: Arceus'
    if 'scarlet' in combined or 'violet' in combined:
        return 'Scarlet/Violet'
    return None


class BulbapediaOutbreaksSpider(scrapy.Spider):
    """
    Scrapes mass outbreak Pokemon data from Bulbapedia for:
    - Legends: Arceus (all regions/areas)
    - Scarlet/Violet (all regions)

    Yields MassOutbreakItem for each Pokemon that can appear in a mass outbreak
    at each location.
    """

    name = "bulbapedia_outbreaks"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = START_URLS

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
    }

    def parse(self, response):
        game = _infer_game(response.url)

        current_region = None

        for el in response.xpath('//h2 | //h3 | //h4 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag in ('h2', 'h3', 'h4'):
                # Region/area headings
                if text and not text.startswith('Content'):
                    current_region = text.strip()

            elif tag == 'table':
                yield from self._parse_outbreak_table(el, game, current_region)

        # Follow sub-page links for individual area outbreak lists
        for link in response.css('a[href*="outbreak"], a[href*="Outbreak"]'):
            href = link.attrib.get('href', '')
            if href and 'bulbapedia' not in href:
                continue
            if href:
                yield response.follow(
                    href,
                    callback=self.parse_subpage,
                    cb_kwargs={'game': game},
                    errback=self.handle_error,
                )

    def parse_subpage(self, response, game):
        """Parse a region-specific outbreak page."""
        current_region = _clean(response.css('h1::text, #firstHeading::text').get(''))
        if not game:
            game = _infer_game(response.url, current_region)

        for el in response.xpath('//h2 | //h3 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag in ('h2', 'h3'):
                current_region = text or current_region

            elif tag == 'table':
                yield from self._parse_outbreak_table(el, game, current_region)

    def _parse_outbreak_table(self, table, game, region):
        """Parse a wikitable listing Pokemon available in mass outbreaks."""
        headers = [_clean(th) for th in table.css('th ::text').getall()[:10]]
        headers_lower = [h.lower() for h in headers]

        def col_idx(*names):
            for name in names:
                for i, h in enumerate(headers_lower):
                    if name in h:
                        return i
            return None

        name_idx = col_idx('pokémon', 'pokemon', 'species', 'name')
        location_idx = col_idx('location', 'area', 'route', 'where')
        notes_idx = col_idx('note', 'special', 'alpha', 'condition')

        for row in table.css('tr'):
            cells = row.css('td')
            if not cells or len(cells) < 1:
                continue

            def cell_text(idx):
                if idx is not None and idx < len(cells):
                    return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            pokemon_name = cell_text(name_idx) if name_idx is not None else cell_text(0)
            # Strip form names like "(Alpha)"
            pokemon_name = re.sub(r'\s*\(.*?\)\s*', ' ', pokemon_name).strip()
            if not pokemon_name or pokemon_name.lower() in ('pokémon', 'pokemon', ''):
                continue

            location = cell_text(location_idx) or region
            notes = cell_text(notes_idx) or None

            yield MassOutbreakItem(
                game=game or 'Unknown',
                region=region,
                location=location or None,
                pokemon_name=pokemon_name,
                notes=notes,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.url}")
