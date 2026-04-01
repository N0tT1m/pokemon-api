import re
import scrapy
from pokemondb_scraper.items import PokemonGameLocationItem

# Reuse the same game title map and helpers from the other Bulbapedia spiders.
# ORDER MATTERS: more-specific patterns before shorter substrings.
GAME_TITLE_MAP = {
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
    'Legends: Arceus':               'Legends: Arceus',
    'Legends: Z-A':                  'Legends: Z-A',
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
    'Colosseum':            'Colosseum',
    'XD: Gale of Darkness': 'XD: Gale of Darkness',
}

# Keywords in location text → method classification.
# Checked in order: first match wins.  More-specific methods come first so
# e.g. "fossil" is not misclassified as "Wild" and "roaming" is not lost.
# Each list entry is a lowercase substring to search for in the location text.
METHOD_KEYWORDS = {
    # ── Event / Mystery Gift (highest priority — always non-standard) ────
    'Event': [
        'event', 'wifi event', 'nintendo event', 'game event',
        'distribution', 'online distribution', 'mystery gift',
        'serial code', 'password', 'qr code',
    ],
    # ── Fossil revival ───────────────────────────────────────────────────
    'Fossil': [
        'fossil', 'revive', 'resurrection', 'lab revival',
        'restore', 'fossil restorer',
    ],
    # ── In-game trades ───────────────────────────────────────────────────
    'Trade': [
        'in-game trade', 'trade for', 'npc trade', 'trade with npc',
        'exchange', 'link trade',
    ],
    # ── Egg / Hatch ───────────────────────────────────────────────────────
    'Hatch': [
        'hatch', 'egg hatching', 'egg (route', 'egg from',
        'mysterious egg', 'egg received', 'egg given',
    ],
    # ── Gift from NPC / starter ───────────────────────────────────────────
    'Gift': [
        'gift', 'starter', 'given by', 'professor',
        'npc gives', 'receive from', 'choice of', 'choose',
        'obtainable from', 'handed', 'awarded', 'reward',
        'birthday', 'game corner prize', 'prize', 'trophy garden gift',
        'nurse joy', 'trade back', 'given to', 'lend',
    ],
    # ── Special / puzzle / mechanic-gated encounters ─────────────────────
    'Special': [
        # Interaction puzzles
        'underground', 'interact', 'odd keystone', 'hallowed tower',
        '32 ', 'braille', 'regi', 'regirock', 'regice', 'registeel',
        'ruins of alph', 'unown', 'dotted hole', 'tanoby',
        'navel rock', 'birth island', 'faraway island',
        # Roaming / wandering
        'roaming', 'roam', 'wanders', 'wander', 'wandering',
        'fly around', 'flies around',
        # Honey / lure / scent
        'honey tree', 'honey', 'headbutt', 'headbutt tree',
        'sweet scent', 'lure',
        # Radar / chain
        'pokeradar', 'poke radar', 'radar', 'chain', 'chaining',
        # SOS / outbreaks / swarms
        'sos', 'sos call', 'swarm', 'outbreak', 'mass outbreak',
        'mass-outbreak', 'pokerus', 'poke pelago',
        # Mirage / island scan / scan
        'mirage', 'island scan', 'island-scan',
        # Time / weather gated
        'only at night', 'only at day', 'only in morning',
        'only during', 'only when', 'only after',
        'rain', 'fog', 'thunderstorm', 'hail',
        # Friend Safari / Dexnav / Pokewalker
        'friend safari', 'safari zone', 'dexnav', 'pokewalker', 'pokéwalker',
        # Grand Underground / Hideaways
        'grand underground', 'hideaway', 'pokémon hideaway', 'pokemon hideaway',
        # Space-time distortion (LA)
        'space-time distortion', 'distortion', 'alabaster',
        # Ultra Wormhole (USUM)
        'ultra wormhole', 'wormhole', 'ultra space',
        # Max Raid / Tera Raid / Dynamax Adventures
        'tera raid', 'max raid', 'raid battle', 'dynamax adventure',
        'crown tundra', 'dynamax den',
        # Union Circle / Herba Mystica (SV)
        'union circle', 'herba mystica',
        # Shrine / altar / temple
        'shrine', 'altar', 'tower of time', 'tower of waters',
        'lugia\'s song', 'tidal bell', 'clear bell', 'rainbow wing',
        'silver wing', 'azure flute', 'oaks letter', 'member card',
        'enigma stone', 'lock capsule',
        # Post-story / version-exclusive flags
        'post-game', 'post game', 'after becoming champion',
        'national pokédex', 'national dex required',
        'show', 'donate', 'bring',
        # Catch combo / Let's Go
        'catch combo', 'lure spawn', 'rare spawn',
        # Specific famous encounters
        'snorlax (requires)', 'feebas tile', 'feebas',
        'corsola (requires', 'tropius (requires',
        'absol (requires', 'bagon (requires',
        'beldum (after', 'larvitar (after',
        'spiritomb', 'odd keystone',
        # Overworld / fixed spawn
        'overworld spawn', 'fixed spawn', 'static encounter',
        'one-time', 'one time only', 'only once',
        # Gym/battle facility rewards
        'battle frontier', 'battle tower', 'battle maison',
        'battle tree', 'battle resort',
    ],
    # ── Roaming (subset of Special, but explicit label) ────────────────
    'Roaming': [
        'roaming', 'roam', 'wanders the', 'wandering the',
        'flies around the', 'fly around the region',
    ],
}


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
    """Strip Pokémon prefix / Version suffix and map to short name."""
    name = re.sub(r'^Pokémon\s+', '', title)
    name = re.sub(r'\s+Versions?$', '', name)
    name = re.sub(r'\s+Version\s*\(Japanese\)$', '', name)
    for pattern, short in GAME_TITLE_MAP.items():
        if pattern in name:
            return short
    return name


def classify_method(location_text):
    """
    Classify acquisition method from location text keywords.
    Checks in dictionary order (Event → Fossil → Trade → Hatch → Gift →
    Special → Roaming) so higher-priority labels win.
    Falls back to 'Wild' if nothing matches.
    """
    lower = location_text.lower()
    for method, keywords in METHOD_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return method
    return 'Wild'


def clean_location(text):
    """Normalise whitespace."""
    return re.sub(r'\s+', ' ', text).strip()


class BulbapediaPokemonLocationsSpider(scrapy.Spider):
    """
    Scrapes the 'Game locations' section from every Pokemon page on Bulbapedia.
    Captures per-game location text including special conditions (e.g. Spiritomb,
    gift Pokemon, fossil revivals, event-only, etc.).
    """
    name = 'bulbapedia_pokemon_locations'
    allowed_domains = ['bulbapedia.bulbagarden.net']
    start_urls = [
        'https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number'
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 2,
        'ROBOTSTXT_OBEY': False,
    }

    def parse(self, response):
        """Follow links to individual Pokemon pages."""
        seen = set()
        for link in response.css('a[href*="_(Pok%C3%A9mon)"]::attr(href)').getall():
            if link not in seen:
                seen.add(link)
                yield response.follow(link, callback=self.parse_pokemon)

        # Paginated list (Generations)
        for next_link in response.css('a[title*="List of Pokémon by National"]::attr(href)').getall():
            if next_link not in seen and 'Generation' in next_link:
                seen.add(next_link)
                yield response.follow(next_link, callback=self.parse)

    def parse_pokemon(self, response):
        """Parse a Pokemon page for its Game locations section."""
        pokemon_name = response.css('h1#firstHeading span::text').get('')
        if not pokemon_name:
            pokemon_name = response.css('h1#firstHeading::text').get('')
        pokemon_name = re.sub(r'\s*\(Pokémon\)\s*$', '', pokemon_name).strip()
        if not pokemon_name:
            return

        # Find the "Game locations" heading (h2 or h3)
        loc_heading = None
        for tag in ('h2', 'h3'):
            loc_heading = response.xpath(
                f'//span[@id="Game_locations"]/ancestor::{tag}'
            )
            if loc_heading:
                break
        if not loc_heading:
            return

        # The locations table immediately follows the heading.
        # Structure: table > tbody > tr
        #   Each row: th (game icons/links) | td (location text)
        # Some pages use a wikitable, some use a roundy wrapper.
        loc_table = loc_heading.xpath(
            'following::table[.//table[@border="1"]][1]//table[@border="1"]'
        )
        if not loc_table:
            loc_table = loc_heading.xpath('following::table[@border="1"][1]')
        if not loc_table:
            loc_table = loc_heading.xpath(
                'following::table[contains(@class,"wikitable")][1]'
            )
        if not loc_table:
            loc_table = loc_heading.xpath('following::table[1]')
        if not loc_table:
            return

        for row in loc_table.xpath('.//tr'):
            # Skip pure-header rows
            if not row.xpath('./td'):
                continue

            th = row.xpath('./th')
            td = row.xpath('./td')
            if not th or not td:
                continue

            # --- Extract game(s) from the th cell ---
            all_link_titles = th.xpath('.//a/@title').getall()
            games = []
            seen_games = set()
            for title in all_link_titles:
                if not is_game_title(title):
                    continue
                game = extract_game_short(title)
                if game and game not in seen_games:
                    seen_games.add(game)
                    games.append(game)

            # Fallback: plain text in th (e.g. "Colo", "XD", abbreviations)
            if not games:
                th_text = ' '.join(th.xpath('.//text()').getall()).strip()
                if th_text and th_text.lower() not in ('games', 'generation'):
                    # Map common abbreviations
                    abbrev_map = {
                        'R': 'Red/Blue', 'B': 'Red/Blue', 'Y': 'Yellow',
                        'G': 'Gold/Silver', 'S': 'Gold/Silver', 'C': 'Crystal',
                        'Fr': 'FireRed/LeafGreen', 'Lg': 'FireRed/LeafGreen',
                        'Colo': 'Colosseum', 'XD': 'XD: Gale of Darkness',
                        'Co': 'Colosseum',
                    }
                    mapped = abbrev_map.get(th_text.strip())
                    if mapped:
                        games = [mapped]
                    else:
                        games = [th_text]

            if not games:
                continue

            # --- Extract location text from td ---
            # May be "Unavailable" / "Not available" — skip those
            raw_text = ' '.join(td.xpath('.//text()').getall())
            location_text = clean_location(raw_text)

            if not location_text:
                continue
            lower = location_text.lower()
            if any(phrase in lower for phrase in (
                'unavailable', 'not available', 'unobtainable',
                'not obtainable', 'not in this game',
            )):
                continue

            method = classify_method(location_text)
            game_str = ', '.join(games)

            yield PokemonGameLocationItem(
                pokemon_name=pokemon_name,
                game=game_str,
                location=location_text,
                method=method,
            )
