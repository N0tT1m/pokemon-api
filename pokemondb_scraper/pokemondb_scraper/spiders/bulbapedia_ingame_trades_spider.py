import re
import scrapy
from pokemondb_scraper.items import InGameTradeItem

# Bulbapedia pages listing in-game trades per game generation
TRADE_PAGES = [
    ('https://bulbapedia.bulbagarden.net/wiki/In-game_trade', None),
]

# Game slug → display name used in our DB
GAME_NAME_MAP = {
    'red': 'Red/Blue', 'blue': 'Red/Blue', 'red/blue': 'Red/Blue',
    'yellow': 'Yellow',
    'gold': 'Gold/Silver', 'silver': 'Gold/Silver', 'gold/silver': 'Gold/Silver',
    'crystal': 'Crystal',
    'ruby': 'Ruby/Sapphire', 'sapphire': 'Ruby/Sapphire', 'ruby/sapphire': 'Ruby/Sapphire',
    'emerald': 'Emerald',
    'firered': 'FireRed/LeafGreen', 'leafgreen': 'FireRed/LeafGreen',
    'firered/leafgreen': 'FireRed/LeafGreen',
    'diamond': 'Diamond/Pearl', 'pearl': 'Diamond/Pearl', 'diamond/pearl': 'Diamond/Pearl',
    'platinum': 'Platinum',
    'heartgold': 'HeartGold/SoulSilver', 'soulsilver': 'HeartGold/SoulSilver',
    'heartgold/soulsilver': 'HeartGold/SoulSilver',
    'black': 'Black/White', 'white': 'Black/White', 'black/white': 'Black/White',
    'black 2': 'Black 2/White 2', 'white 2': 'Black 2/White 2',
    'x': 'X/Y', 'y': 'X/Y', 'x/y': 'X/Y',
    'omega ruby': 'Omega Ruby/Alpha Sapphire', 'alpha sapphire': 'Omega Ruby/Alpha Sapphire',
    'omega ruby/alpha sapphire': 'Omega Ruby/Alpha Sapphire',
    'sun': 'Sun/Moon', 'moon': 'Sun/Moon', 'sun/moon': 'Sun/Moon',
    'ultra sun': 'Ultra Sun/Ultra Moon', 'ultra moon': 'Ultra Sun/Ultra Moon',
    "let's go pikachu": "Let's Go Pikachu/Eevee", "let's go eevee": "Let's Go Pikachu/Eevee",
    'sword': 'Sword/Shield', 'shield': 'Sword/Shield', 'sword/shield': 'Sword/Shield',
    'brilliant diamond': 'Brilliant Diamond/Shining Pearl',
    'shining pearl': 'Brilliant Diamond/Shining Pearl',
    'scarlet': 'Scarlet/Violet', 'violet': 'Scarlet/Violet', 'scarlet/violet': 'Scarlet/Violet',
    'legends: arceus': 'Legends: Arceus', 'legends: z-a': 'Legends: Z-A',
}


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _normalize_game(text):
    """Map raw game text to our standard game name."""
    t = text.strip().lower()
    for key, val in GAME_NAME_MAP.items():
        if key in t:
            return val
    return text.strip()


def _parse_int(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


class BulbapediaInGameTradesSpider(scrapy.Spider):
    """
    Scrapes in-game NPC trade data from Bulbapedia's in-game trade article.

    Yields InGameTradeItem for each trade: what you give, what you receive,
    the NPC name, location, and any special notes.
    """

    name = "bulbapedia_ingame_trades"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = [p[0] for p in TRADE_PAGES]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
    }

    def parse(self, response):
        # The in-game trade page is organized by generation (h2) and game (h3).
        # Each trade is in a table with columns: Receive, Give, Location, Notes, etc.
        current_game = None

        for el in response.xpath('//h2 | //h3 | //table[has-class("wikitable")]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag == 'h2':
                # Generation heading — reset game context
                current_game = None

            elif tag == 'h3':
                # Game heading
                current_game = _normalize_game(text) if text else None

            elif tag == 'table' and current_game:
                yield from self._parse_trade_table(el, current_game)

        # Also follow any sub-pages linked from the main article
        for link in response.css('a[href*="in-game_trade"]'):
            href = link.attrib.get('href', '')
            if href and href != response.url:
                yield response.follow(href, callback=self.parse_subpage)

    def parse_subpage(self, response):
        """Parse a game-specific in-game trade sub-page."""
        # Determine game from page title
        title = _clean(response.css('h1::text, #firstHeading::text').get(''))
        game = _normalize_game(title)

        for table in response.css('table.wikitable'):
            yield from self._parse_trade_table(table, game)

    def _parse_trade_table(self, table, game):
        """Parse a wikitable of trades for a given game."""
        headers = [_clean(th) for th in table.css('th ::text').getall()[:10]]
        headers_lower = [h.lower() for h in headers]

        def col_idx(*names):
            for name in names:
                for i, h in enumerate(headers_lower):
                    if name in h:
                        return i
            return None

        receive_idx = col_idx('receive', 'obtained', 'gets')
        give_idx = col_idx('give', 'traded', 'offer', 'player gives')
        location_idx = col_idx('location', 'where', 'place')
        npc_idx = col_idx('npc', 'trader', 'name', 'given by')
        level_idx = col_idx('level', 'lv')
        item_idx = col_idx('held item', 'item')
        notes_idx = col_idx('note', 'special', 'condition')

        for row in table.css('tr'):
            cells = row.css('td')
            if not cells or len(cells) < 2:
                continue

            def cell_text(idx):
                if idx is not None and idx < len(cells):
                    return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            offered_pokemon = cell_text(receive_idx) if receive_idx is not None else cell_text(0)
            requested_pokemon = cell_text(give_idx) if give_idx is not None else cell_text(1)

            if not offered_pokemon or not requested_pokemon:
                continue

            yield InGameTradeItem(
                game=game,
                location=cell_text(location_idx) or None,
                offered_pokemon=offered_pokemon,
                offered_level=_parse_int(cell_text(level_idx)),
                offered_item=cell_text(item_idx) or None,
                requested_pokemon=requested_pokemon,
                npc_name=cell_text(npc_idx) or None,
                notes=cell_text(notes_idx) or None,
            )
