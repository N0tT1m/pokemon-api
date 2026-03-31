import re
import scrapy
from pokemondb_scraper.items import WildHeldItemItem, PokemonBiologyItem


def is_game_title(title):
    """Return True only if a Bulbapedia link title refers to an actual Pokemon game."""
    if not (title.startswith('Pokémon ') or title.startswith('Pokémon:')):
        return False
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


def extract_game_short(title):
    """Extract short game name from Bulbapedia link title."""
    name = re.sub(r'^Pokémon\s+', '', title)
    name = re.sub(r'\s+Versions?$', '', name)
    name = re.sub(r'\s+Version\s*\(Japanese\)$', '', name)
    # ORDER MATTERS: more-specific (longer) patterns must come before any shorter
    # pattern that is a substring of them (e.g. 'Omega Ruby' before 'Ruby').
    mapping = {
        # ── Paired / combined article titles ─────────────────────────────
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
        # ── Legends titles ────────────────────────────────────────────────
        'Legends: Arceus': 'Legends: Arceus',
        'Legends: Z-A':    'Legends: Z-A',
        # ── Multi-word individual titles (before any single-word subset) ──
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
        # ── Single-word titles ─────────────────────────────────────────────
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
        # ── Spin-offs ──────────────────────────────────────────────────────
        'Colosseum':            'Colosseum',
        'XD: Gale of Darkness': 'XD: Gale of Darkness',
    }
    for pattern, short in mapping.items():
        if pattern in name:
            return short
    return name


class BulbapediaPokemonSpider(scrapy.Spider):
    """Scrapes wild held items and biology text from Bulbapedia Pokemon pages."""
    name = "bulbapedia_pokemon"
    allowed_domains = ["bulbapedia.bulbagarden.net"]
    start_urls = ["https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 2,
        'ROBOTSTXT_OBEY': True,
    }

    def parse(self, response):
        """Follow links to individual Pokemon pages from the National Dex list."""
        seen = set()
        for link in response.css('a[href*="_(Pok%C3%A9mon)"]::attr(href)').getall():
            if link not in seen:
                seen.add(link)
                yield response.follow(link, callback=self.parse_pokemon)

        # Follow next page links if paginated
        for next_link in response.css('a[title*="List of Pokémon by National"]::attr(href)').getall():
            if next_link not in seen and 'Generation' in next_link:
                seen.add(next_link)
                yield response.follow(next_link, callback=self.parse)

    def parse_pokemon(self, response):
        """Parse a Pokemon page for held items and biology."""
        pokemon_name = response.css('h1#firstHeading span::text').get('')
        if not pokemon_name:
            pokemon_name = response.css('h1#firstHeading::text').get('')
        pokemon_name = pokemon_name.strip()

        # Remove " (Pokémon)" suffix
        pokemon_name = re.sub(r'\s*\(Pokémon\)\s*$', '', pokemon_name)
        if not pokemon_name:
            return

        # --- Biology ---
        bio_heading = response.xpath('//span[@id="Biology"]/ancestor::h2')
        if bio_heading:
            paragraphs = []
            for sibling in bio_heading.xpath('following-sibling::*'):
                tag = sibling.xpath('name()').get('')
                if tag in ('h2', 'h3'):
                    break
                if tag == 'p':
                    text = ' '.join(sibling.xpath('.//text()').getall())
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        paragraphs.append(text)
            if paragraphs:
                yield PokemonBiologyItem(
                    pokemon_name=pokemon_name,
                    biology='\n\n'.join(paragraphs),
                )

        # --- Wild Held Items ---
        held_heading = response.xpath('//span[@id="Held_items"]/ancestor::h3 | //span[@id="Held_items"]/ancestor::h4')
        if not held_heading:
            return

        # Find the held items table (has "Held items" in header)
        held_table = held_heading.xpath(
            'following::table[.//th[contains(text(), "Held items")]][1]'
        )
        if not held_table:
            return

        for row in held_table.xpath('.//tr'):
            # Skip header row
            if row.xpath('./th[contains(text(), "Held items")]'):
                continue

            # Get game names from th cells with links — filter to actual game titles only
            all_link_titles = row.xpath('.//th//a/@title').getall()
            games = []
            for title in all_link_titles:
                if not is_game_title(title):
                    continue
                game = extract_game_short(title)
                if game and game not in games:
                    games.append(game)

            # Also check for non-linked game text in th (e.g., "Colo", "XD")
            if not games:
                th_text = ' '.join(row.xpath('.//th//text()').getall()).strip()
                if th_text and th_text != 'Games':
                    games = [th_text]

            if not games:
                continue

            game_str = ', '.join(games)

            # Get held items from td - each item is in a div with item name link and rarity
            td = row.xpath('./td')
            if not td:
                continue

            for item_div in td.xpath('.//div[.//a[not(contains(@href, "File:"))]]'):
                item_links = item_div.xpath('.//a[not(contains(@href, "File:"))]')
                item_name = ''
                for link in item_links:
                    text = link.xpath('./text()').get('').strip()
                    href = link.xpath('./@href').get('')
                    # Skip links that are Pokemon names or other non-item links
                    if text and '/wiki/' in href and 'Pok%C3%A9mon' not in href:
                        item_name = text
                        break

                if not item_name:
                    continue

                # Extract rarity - look for percentage in parentheses
                div_text = ' '.join(item_div.xpath('.//text()').getall())
                rarity_match = re.search(r'(\d+%)', div_text)
                rarity = rarity_match.group(1) if rarity_match else ''

                yield WildHeldItemItem(
                    pokemon_name=pokemon_name,
                    game=game_str,
                    item_name=item_name,
                    rarity=rarity,
                )
