import re
import scrapy
from pokemondb_scraper.items import ItemLocationItem

# Map Bulbapedia game title patterns to short game names
GAME_TITLE_MAP = {
    'Red and Blue': 'Red/Blue',
    'Red and Green': 'Red/Green',
    'Yellow': 'Yellow',
    'Gold and Silver': 'Gold/Silver',
    'Crystal': 'Crystal',
    'Ruby and Sapphire': 'Ruby/Sapphire',
    'Emerald': 'Emerald',
    'FireRed and LeafGreen': 'FireRed/LeafGreen',
    'Diamond and Pearl': 'Diamond/Pearl',
    'Platinum': 'Platinum',
    'HeartGold and SoulSilver': 'HeartGold/SoulSilver',
    'Black and White': 'Black/White',
    'Black 2 and White 2': 'Black 2/White 2',
    'X and Y': 'X/Y',
    'Omega Ruby and Alpha Sapphire': 'Omega Ruby/Alpha Sapphire',
    'Sun and Moon': 'Sun/Moon',
    'Ultra Sun and Ultra Moon': 'Ultra Sun/Ultra Moon',
    "Let's Go, Pikachu! and Let's Go, Eevee!": "Let's Go Pikachu/Eevee",
    'Sword and Shield': 'Sword/Shield',
    'Brilliant Diamond and Shining Pearl': 'Brilliant Diamond/Shining Pearl',
    'Legends: Arceus': 'Legends: Arceus',
    'Scarlet and Violet': 'Scarlet/Violet',
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
        'ROBOTSTXT_OBEY': True,
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

        # Find the Acquisition section
        acq_heading = response.xpath('//span[@id="Acquisition"]/ancestor::h3')
        if not acq_heading:
            acq_heading = response.xpath('//span[@id="Acquisition"]/ancestor::h4')
        if not acq_heading:
            return

        # Find the acquisition table (border="1" table after the heading)
        acq_table = acq_heading.xpath(
            'following::table[.//table[@border="1"]][1]//table[@border="1"]'
        )
        if not acq_table:
            # Try direct sibling
            acq_table = acq_heading.xpath('following::table[@border="1"][1]')
        if not acq_table:
            return

        for row in acq_table.xpath('.//tbody/tr'):
            cells = row.xpath('./td')
            if len(cells) < 2:
                continue

            # Cell 0: Games
            games_cell = cells[0]
            # Extract game names from link titles
            game_titles = games_cell.xpath('.//a[contains(@title, "Pokémon")]/@title').getall()
            games = []
            for title in game_titles:
                game = extract_game_name(title)
                if game and game not in games:
                    games.append(game)

            # Also check for non-linked game text (Colo, XD, etc.)
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

            # Determine method based on content
            method = None
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
