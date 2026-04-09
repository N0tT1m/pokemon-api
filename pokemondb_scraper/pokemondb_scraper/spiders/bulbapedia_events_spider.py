import re
import scrapy
from pokemondb_scraper.items import EventPokemonItem

# Main event distribution list page on Bulbapedia
START_URLS = [
    'https://bulbapedia.bulbagarden.net/wiki/List_of_local_event_Pok%C3%A9mon_distributions_(Generation_V)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_local_event_Pok%C3%A9mon_distributions_(Generation_VI)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_local_event_Pok%C3%A9mon_distributions_(Generation_VII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_local_event_Pok%C3%A9mon_distributions_(Generation_VIII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_local_event_Pok%C3%A9mon_distributions_(Generation_IX)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_Wi-Fi_event_Pok%C3%A9mon_distributions_(Generation_V)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_Wi-Fi_event_Pok%C3%A9mon_distributions_(Generation_VI)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_Wi-Fi_event_Pok%C3%A9mon_distributions_(Generation_VII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_Wi-Fi_event_Pok%C3%A9mon_distributions_(Generation_VIII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_serial_code_event_Pok%C3%A9mon_distributions_(Generation_VI)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_serial_code_event_Pok%C3%A9mon_distributions_(Generation_VII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_serial_code_event_Pok%C3%A9mon_distributions_(Generation_VIII)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_serial_code_event_Pok%C3%A9mon_distributions_(Generation_IX)',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_in-game_event_Pok%C3%A9mon_in_Pok%C3%A9mon_Legends:_Z-A',
]

GEN_DISTRIBUTION_MAP = {
    'Generation_V': 'Black/White',
    'Generation_VI': 'X/Y',
    'Generation_VII': 'Sun/Moon',
    'Generation_VIII': 'Sword/Shield',
    'Generation_IX': 'Scarlet/Violet',
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_int(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


def _parse_year(text):
    m = re.search(r'(20\d{2}|19\d{2})', text or '')
    return int(m.group(1)) if m else None


def _extract_distribution_method(url):
    """Infer distribution method from the page URL."""
    if 'Wi-Fi' in url or 'wifi' in url.lower():
        return 'Wi-Fi'
    if 'serial' in url.lower():
        return 'Serial Code'
    if 'local' in url.lower():
        return 'Local Wireless'
    if 'in-game' in url.lower():
        return 'In-Game'
    return None


class BulbapediaEventsSpider(scrapy.Spider):
    """
    Scrapes historical event/distribution Pokemon from Bulbapedia event lists.

    Yields EventPokemonItem for each distribution event, capturing the Pokemon,
    game, year, level, held item, moves, OT name, and distribution method.
    """

    name = "bulbapedia_events"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = START_URLS

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        distribution_method = _extract_distribution_method(response.url)

        # Infer generation/game from URL
        gen_game = None
        for gen_key, game_name in GEN_DISTRIBUTION_MAP.items():
            if gen_key in response.url:
                gen_game = game_name
                break

        current_game = gen_game
        current_year = None

        for el in response.xpath('//h2 | //h3 | //h4 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag in ('h2', 'h3', 'h4'):
                # Try to extract year from section heading
                year = _parse_year(text)
                if year:
                    current_year = year
                # Game name sometimes appears in headings too
                if any(kw in text for kw in ('Scarlet', 'Violet', 'Sword', 'Shield', 'Sun', 'Moon',
                                              'X', 'Y', 'Black', 'White', 'Diamond', 'Pearl')):
                    current_game = text.strip()

            elif tag == 'table':
                yield from self._parse_event_table(
                    el, current_game, current_year, distribution_method
                )

    def _parse_event_table(self, table, game, year, distribution_method):
        """Parse a wikitable of event distributions."""
        headers = [_clean(th) for th in table.css('th ::text').getall()[:15]]
        headers_lower = [h.lower() for h in headers]

        def col_idx(*names):
            for name in names:
                for i, h in enumerate(headers_lower):
                    if name in h:
                        return i
            return None

        name_idx = col_idx('pokémon', 'pokemon', 'name', 'species')
        level_idx = col_idx('level', 'lv.')
        item_idx = col_idx('held item', 'item')
        ot_idx = col_idx('ot', 'original trainer', 'trainer name')
        moves_idx = col_idx('move', 'attack')
        notes_idx = col_idx('note', 'remarks', 'special')
        year_idx = col_idx('year', 'date')

        for row in table.css('tr'):
            cells = row.css('td')
            if not cells or len(cells) < 2:
                continue

            def cell_text(idx):
                if idx is not None and idx < len(cells):
                    return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            pokemon_name = cell_text(name_idx) if name_idx is not None else cell_text(0)
            # Remove form suffixes like "(Black Kyurem)"
            pokemon_name = re.sub(r'\s*\(.*?\)\s*', '', pokemon_name).strip()
            if not pokemon_name or pokemon_name.lower() in ('pokémon', 'pokemon', ''):
                continue

            event_year = _parse_year(cell_text(year_idx)) if year_idx else year

            # Moves may be in multiple columns
            moves = []
            if moves_idx is not None:
                for mi in range(moves_idx, min(moves_idx + 4, len(cells))):
                    move = cell_text(mi)
                    if move and move not in ('—', '-', ''):
                        moves.append(move)

            yield EventPokemonItem(
                name=pokemon_name,
                game=game,
                year=event_year,
                level=_parse_int(cell_text(level_idx)),
                held_item=cell_text(item_idx) or None,
                moves=moves if moves else None,
                ot_name=cell_text(ot_idx) or None,
                distribution_method=distribution_method,
                notes=cell_text(notes_idx) or None,
            )
