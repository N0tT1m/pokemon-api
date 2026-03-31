import re
import scrapy
from pokemondb_scraper.items import TmLocationItem


def extract_game_short(title):
    """Extract short game name from Bulbapedia link title."""
    name = re.sub(r'^Pokémon\s+', '', title)
    name = re.sub(r'\s+Versions?$', '', name)
    name = re.sub(r'\s+Version\s*\(Japanese\)$', '', name)
    mapping = {
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
    for pattern, short in mapping.items():
        if pattern in name:
            return short
    return name


class BulbapediaTmLocationsSpider(scrapy.Spider):
    """Scrapes TM/HM location data from individual TM pages on Bulbapedia."""
    name = "bulbapedia_tm_locations"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    # Start from the TM disambiguation / list page
    start_urls = ["https://bulbapedia.bulbagarden.net/wiki/TM"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 2,
        'ROBOTSTXT_OBEY': True,
    }

    def parse(self, response):
        """Find links to individual TM pages (TM01, TM02, etc.)."""
        seen = set()
        for link in response.css('a[href*="/wiki/TM"]::attr(href)').getall():
            # Match TM01-TM999 and HM01-HM08
            match = re.search(r'/wiki/((?:TM|HM)\d+)$', link)
            if match and link not in seen:
                seen.add(link)
                yield response.follow(link, callback=self.parse_tm_page)

    def parse_tm_page(self, response):
        """Parse an individual TM/HM page for location data per generation."""
        page_title = response.css('h1#firstHeading span::text').get('')
        if not page_title:
            page_title = response.css('h1#firstHeading::text').get('')
        tm_number = page_title.strip()
        if not tm_number:
            return

        # Find the "In the core series games" section
        core_section = response.xpath(
            '//span[@id="In_the_core_series_games"]/ancestor::h2'
        )
        if not core_section:
            return

        # Walk through generation sub-sections
        # Structure per generation:
        #   h3 "Generation X"
        #   table with move name row
        #   table/rows with: [games | Location | Purchase price | Sell price]
        current_move = ''

        for element in core_section.xpath('following-sibling::*'):
            tag = element.xpath('name()').get('')

            # Stop at the next h2 (e.g., "In the spin-off games")
            if tag == 'h2':
                break

            # Pick up move name from the small table that shows the move
            if tag == 'table':
                # Check if this is a move name table (has 3 cells in first row)
                first_row = element.xpath('.//tr[1]')
                move_cell = first_row.xpath('.//td[last()]')
                if move_cell:
                    move_text = move_cell.xpath('.//text()').get('').strip()
                    if move_text and not move_text.startswith('$') and move_text != 'Location':
                        current_move = move_text

                # Check if this is a location table (has "Location" header)
                has_location = element.xpath('.//th[contains(text(), "Location")]')
                if not has_location:
                    continue

                for row in element.xpath('.//tr'):
                    cells = row.xpath('./td')
                    if len(cells) < 2:
                        continue

                    # First cell: game abbreviations
                    game_cell = cells[0]
                    # Try link titles first
                    game_titles = game_cell.xpath('.//a[contains(@title, "Pokémon")]/@title').getall()
                    games = []
                    for title in game_titles:
                        game = extract_game_short(title)
                        if game and game not in games:
                            games.append(game)
                    # Fallback to text
                    if not games:
                        game_text = ' '.join(game_cell.xpath('.//text()').getall()).strip()
                        if game_text:
                            games = [game_text]

                    if not games:
                        continue

                    # Second cell: location
                    location_text = ' '.join(cells[1].xpath('.//text()').getall())
                    location_text = re.sub(r'\s+', ' ', location_text).strip()

                    if not location_text:
                        continue

                    game_str = ', '.join(games)

                    yield TmLocationItem(
                        tm_number=tm_number,
                        move_name=current_move,
                        game=game_str,
                        location=location_text,
                    )
