import re
import scrapy
from pokemondb_scraper.items import MoveTutorLocationItem

# Bulbapedia move tutor pages — one per generation/game that has tutors
TUTOR_PAGES = [
    'https://bulbapedia.bulbagarden.net/wiki/Move_Tutor',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_II',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_III',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_IV',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_V',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_VI',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_VII',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_VIII',
    'https://bulbapedia.bulbagarden.net/wiki/List_of_move_tutors_in_Generation_IX',
]

GAME_NAME_MAP = {
    'crystal': 'Crystal',
    'firered': 'FireRed/LeafGreen', 'leafgreen': 'FireRed/LeafGreen',
    'emerald': 'Emerald',
    'diamond': 'Diamond/Pearl', 'pearl': 'Diamond/Pearl',
    'platinum': 'Platinum',
    'heartgold': 'HeartGold/SoulSilver', 'soulsilver': 'HeartGold/SoulSilver',
    'black': 'Black/White', 'white': 'Black/White',
    'black 2': 'Black 2/White 2', 'white 2': 'Black 2/White 2',
    'x': 'X/Y', 'y': 'X/Y',
    'omega ruby': 'Omega Ruby/Alpha Sapphire', 'alpha sapphire': 'Omega Ruby/Alpha Sapphire',
    'sun': 'Sun/Moon', 'moon': 'Sun/Moon',
    'ultra sun': 'Ultra Sun/Ultra Moon', 'ultra moon': 'Ultra Sun/Ultra Moon',
    'sword': 'Sword/Shield', 'shield': 'Sword/Shield',
    'brilliant diamond': 'Brilliant Diamond/Shining Pearl',
    'shining pearl': 'Brilliant Diamond/Shining Pearl',
    'scarlet': 'Scarlet/Violet', 'violet': 'Scarlet/Violet',
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _normalize_game(text):
    lower = text.lower().strip()
    for key, val in GAME_NAME_MAP.items():
        if key in lower:
            return val
    return text.strip()


class BulbapediaMoveTutorsSpider(scrapy.Spider):
    """
    Scrapes move tutor NPC locations and costs from Bulbapedia.

    Yields MoveTutorLocationItem: which moves each tutor teaches, in which game,
    at what location, for what cost (BP, shards, free, etc.).
    """

    name = "bulbapedia_move_tutors"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = TUTOR_PAGES

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        current_game = None

        for el in response.xpath('//h2 | //h3 | //h4 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag in ('h2', 'h3', 'h4'):
                # Game heading
                game = _normalize_game(text)
                if game and game != text:  # only update if we recognized the game
                    current_game = game
                elif any(kw in text.lower() for kw in ('tutor', 'move', 'teach')):
                    pass  # generic section — keep current game
                else:
                    current_game = game or current_game

            elif tag == 'table' and current_game:
                yield from self._parse_tutor_table(el, current_game)

        # Follow sub-page links for generation-specific tutor lists
        for link in response.css('a[href*="move_tutor"], a[href*="Move_Tutor"], a[href*="tutor"]'):
            href = link.attrib.get('href', '')
            if href and 'bulbapedia' not in href and not href.startswith('/wiki/'):
                continue
            if href:
                yield response.follow(href, callback=self.parse, errback=self.handle_error)

    def _parse_tutor_table(self, table, game):
        """
        Parse a move tutor table. Columns vary but typically:
          Move | Location | Cost | Notes
        or
          Move | Tutor | Location | Cost
        """
        headers = [_clean(th) for th in table.css('th ::text').getall()[:10]]
        headers_lower = [h.lower() for h in headers]

        def col_idx(*names):
            for name in names:
                for i, h in enumerate(headers_lower):
                    if name in h:
                        return i
            return None

        move_idx = col_idx('move', 'attack', 'name')
        location_idx = col_idx('location', 'area', 'where', 'place', 'city')
        cost_idx = col_idx('cost', 'price', 'bp', 'shard', 'exchange')
        tutor_idx = col_idx('tutor', 'npc', 'person')

        for row in table.css('tr'):
            cells = row.css('td')
            if not cells or len(cells) < 1:
                continue

            def cell_text(idx):
                if idx is not None and idx < len(cells):
                    return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            move_name = cell_text(move_idx) if move_idx is not None else cell_text(0)
            if not move_name or move_name.lower() in ('move', ''):
                continue

            location = cell_text(location_idx)
            if tutor_idx is not None:
                tutor_loc = cell_text(tutor_idx)
                if tutor_loc and not location:
                    location = tutor_loc
                elif tutor_loc:
                    location = f"{tutor_loc}, {location}"

            cost = cell_text(cost_idx) or None

            yield MoveTutorLocationItem(
                move_name=move_name,
                game=game,
                location=location or None,
                cost=cost,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.url}")
