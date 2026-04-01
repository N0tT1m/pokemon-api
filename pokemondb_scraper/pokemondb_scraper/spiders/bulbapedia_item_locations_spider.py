import re
import scrapy
from pokemondb_scraper.items import ItemLocationItem

# Map Bulbapedia game title patterns to short game names.
# ORDER MATTERS: more-specific (longer) patterns must come before any shorter
# pattern that is a substring of them (e.g. 'Omega Ruby' before 'Ruby').
GAME_TITLE_MAP = {
    # ── Paired / combined article titles ─────────────────────────────────
    'Omega Ruby and Alpha Sapphire': 'Omega Ruby/Alpha Sapphire',
    'Ultra Sun and Ultra Moon':      'Ultra Sun/Ultra Moon',
    "Let's Go, Pikachu! and Let's Go, Eevee!": "Let's Go Pikachu/Eevee",
    'Brilliant Diamond and Shining Pearl': 'Brilliant Diamond/Shining Pearl',
    'HeartGold and SoulSilver':      'HeartGold/SoulSilver',
    'Black 2 and White 2':           'Black 2/White 2',
    'FireRed and LeafGreen':         'FireRed/LeafGreen',
    'Red and Blue':                  'Red/Blue',
    'Red and Green':                 'Red/Green',
    'Gold and Silver':               'Gold/Silver',
    'Ruby and Sapphire':             'Ruby/Sapphire',
    'Diamond and Pearl':             'Diamond/Pearl',
    'Black and White':               'Black/White',
    'Scarlet and Violet':            'Scarlet/Violet',
    'Sword and Shield':              'Sword/Shield',
    'Sun and Moon':                  'Sun/Moon',
    'X and Y':                       'X/Y',
    # ── Legends titles ────────────────────────────────────────────────────
    'Legends: Arceus': 'Legends: Arceus',
    'Legends: Z-A':    'Legends: Z-A',
    # ── Multi-word individual titles (before any single-word subset) ──────
    'Black 2':          'Black 2/White 2',
    'White 2':          'Black 2/White 2',
    'Omega Ruby':       'Omega Ruby/Alpha Sapphire',
    'Alpha Sapphire':   'Omega Ruby/Alpha Sapphire',
    'Ultra Sun':        'Ultra Sun/Ultra Moon',
    'Ultra Moon':       'Ultra Sun/Ultra Moon',
    'Brilliant Diamond':'Brilliant Diamond/Shining Pearl',
    'Shining Pearl':    'Brilliant Diamond/Shining Pearl',
    'HeartGold':        'HeartGold/SoulSilver',
    'SoulSilver':       'HeartGold/SoulSilver',
    'FireRed':          'FireRed/LeafGreen',
    'LeafGreen':        'FireRed/LeafGreen',
    "Let's Go, Pikachu!": "Let's Go Pikachu/Eevee",
    "Let's Go, Eevee!":   "Let's Go Pikachu/Eevee",
    # ── Single-word titles ────────────────────────────────────────────────
    'Yellow':   'Yellow',
    'Crystal':  'Crystal',
    'Emerald':  'Emerald',
    'Platinum': 'Platinum',
    'Red':      'Red/Blue',
    'Blue':     'Red/Blue',
    'Green':    'Red/Green',
    'Gold':     'Gold/Silver',
    'Silver':   'Gold/Silver',
    'Ruby':     'Ruby/Sapphire',
    'Sapphire': 'Ruby/Sapphire',
    'Diamond':  'Diamond/Pearl',
    'Pearl':    'Diamond/Pearl',
    'Black':    'Black/White',
    'White':    'Black/White',
    'X':        'X/Y',
    'Y':        'X/Y',
    'Sun':      'Sun/Moon',
    'Moon':     'Sun/Moon',
    'Sword':    'Sword/Shield',
    'Shield':   'Sword/Shield',
    'Scarlet':  'Scarlet/Violet',
    'Violet':   'Scarlet/Violet',
    # ── Spin-offs ─────────────────────────────────────────────────────────
    'Colosseum':            'Colosseum',
    'XD: Gale of Darkness': 'XD: Gale of Darkness',
}


def extract_game_name(title):
    """Extract a short game name from a Bulbapedia page title like 'Pokémon Red and Blue Versions'."""
    # Remove 'Pokémon ' prefix and ' Version(s)' suffix
    name = re.sub(r'^Pokémon\s+', '', title)
    name = re.sub(r'\s+Versions?$', '', name)
    name = re.sub(r'\s+Version\s*\(Japanese\)$', '', name)

    for pattern, short in GAME_TITLE_MAP.items():
        if pattern in name:
            return short
    return name


def clean_text(html_text):
    """Strip HTML tags and clean whitespace."""
    text = re.sub(r'<[^>]+>', '', html_text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class BulbapediaItemLocationsSpider(scrapy.Spider):
    name = "bulbapedia_item_locations"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = ["https://bulbapedia.bulbagarden.net/wiki/List_of_items_by_name"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 2,
        'ROBOTSTXT_OBEY': False,
    }

    def parse(self, response):
        """Parse the item list page and follow links to individual item pages."""
        # Items are in table rows: sprite | name link | gen | description
        for row in response.css('table.sortable tr'):
            link = row.css('td:nth-child(2) a::attr(href)').get()
            if link and '/wiki/' in link:
                yield response.follow(link, callback=self.parse_item_page)

    def parse_item_page(self, response):
        """Parse an individual item page for acquisition data."""
        item_name = response.css('h1#firstHeading span::text').get('')
        if not item_name:
            item_name = response.css('h1#firstHeading::text').get('')
        item_name = item_name.strip()
        if not item_name:
            return

        # Helper: decide if a link title is a game title (not a species/place/misc page)
        def is_game_title(title):
            if not (title.startswith('Pokémon ') or title.startswith('Pokémon:')):
                return False
            # Exclude known non-game pages
            for skip in [
                '(Pokémon)', 'Pokémon Adventures', 'Pokémon the Series',
                'List of Pokémon', 'Pokémon Center', 'Pokémon Trainer',
                'Pokémon Horizons', 'Pokémon GO', 'Pokémon HOME',
                'Pokémon UNITE', 'Pokémon Masters', 'Pokémon Stadium',
                'Pokémon Snap', 'Pokémon Ranger', 'Pokémon Mystery Dungeon',
                'Pokémon Rumble', 'Pokémon Pinball', 'Pokémon Conquest',
            ]:
                if skip in title:
                    return False
            # Accept titles that reference any known game keyword
            if re.search(
                r'Version|Colosseum|XD:|Legends:'
                r'|FireRed|LeafGreen|HeartGold|SoulSilver'
                r'|Omega Ruby|Alpha Sapphire|Brilliant Diamond|Shining Pearl'
                r'|Ultra Sun|Ultra Moon|Let.s Go'
                r'|Sword and Shield|\bSword\b|\bShield\b'
                r'|Scarlet and Violet|\bScarlet\b|\bViolet\b'
                r'|Sun and Moon|\bSun\b|\bMoon\b'
                r'|X and Y|\bX\b|\bY\b',
                title,
            ):
                return True
            return False

        # Find the Acquisition or Availability section heading (h2, h3, or h4)
        acq_heading = None
        for section_id in ('Acquisition', 'Availability'):
            for tag in ('h3', 'h4', 'h2'):
                acq_heading = response.xpath(
                    f'//span[@id="{section_id}"]/ancestor::{tag}'
                )
                if acq_heading:
                    break
            if acq_heading:
                break
        if not acq_heading:
            return

        # Find the acquisition table.
        # Bulbapedia wraps the data table (border="1") inside an outer roundy table.
        acq_table = acq_heading.xpath(
            'following::table[.//table[@border="1"]][1]//table[@border="1"]'
        )
        if not acq_table:
            # Try a direct border="1" table (no wrapper)
            acq_table = acq_heading.xpath('following::table[@border="1"][1]')
        if not acq_table:
            # Fallback: wikitable class
            acq_table = acq_heading.xpath('following::table[contains(@class,"wikitable")][1]')
        if not acq_table:
            return

        for row in acq_table.xpath('.//tbody/tr'):
            # Skip header rows (th cells only)
            cells = row.xpath('./td')
            if len(cells) < 2:
                continue

            # Cell 0: Games — extract game names from link titles
            games_cell = cells[0]
            all_link_titles = games_cell.xpath('.//a/@title').getall()
            games = []
            seen_games = set()
            for title in all_link_titles:
                if not is_game_title(title):
                    continue
                game = extract_game_name(title)
                if game and game not in seen_games:
                    seen_games.add(game)
                    games.append(game)

            # Fallback: use raw cell text if no game links were recognised
            if not games:
                cell_text = clean_text(cells[0].get())
                if cell_text:
                    games = [cell_text]

            if not games:
                continue

            game_str = ', '.join(games)

            # Cell 1: Finite methods (locations)
            finite_text = clean_text(cells[1].get()) if len(cells) > 1 else ''
            # Cell 2: Repeatable methods
            repeat_text = clean_text(cells[2].get()) if len(cells) > 2 else ''

            # Combine locations
            locations = []
            if finite_text:
                locations.append(finite_text)
            if repeat_text:
                locations.append(repeat_text)

            if not locations:
                continue

            location_str = '; '.join(locations)

            # Determine method based on which columns have content
            if repeat_text and not finite_text:
                method = 'Repeatable'
            elif finite_text and not repeat_text:
                method = 'Finite'
            else:
                method = 'Finite & Repeatable'

            yield ItemLocationItem(
                item_name=item_name,
                game=game_str,
                location=location_str,
                method=method,
            )
