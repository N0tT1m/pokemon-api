import re

import scrapy

from pokemondb_scraper.items import TrainerItem, TrainerPokemonItem

# Game slug → display name for games that have a gymleaders-elitefour page.
# Legends: Arceus and DLC packs don't have gym leader structures, so they're excluded.
GAME_PAGES = {
    'red-blue':                    'Red/Blue',
    'yellow':                      'Yellow',
    'gold-silver':                 'Gold/Silver',
    'crystal':                     'Crystal',
    'ruby-sapphire':               'Ruby/Sapphire',
    'emerald':                     'Emerald',
    'firered-leafgreen':           'FireRed/LeafGreen',
    'diamond-pearl':               'Diamond/Pearl',
    'platinum':                    'Platinum',
    'heartgold-soulsilver':        'HeartGold/SoulSilver',
    'black-white':                 'Black/White',
    'black-white-2':               'Black 2/White 2',
    'x-y':                         'X/Y',
    'omega-ruby-alpha-sapphire':   'Omega Ruby/Alpha Sapphire',
    'sun-moon':                    'Sun/Moon',
    'ultra-sun-ultra-moon':        'Ultra Sun/Ultra Moon',
    'lets-go-pikachu-eevee':       "Let's Go Pikachu/Eevee",
    'sword-shield':                'Sword/Shield',
    'brilliant-diamond-shining-pearl': 'Brilliant Diamond/Shining Pearl',
    'scarlet-violet':              'Scarlet/Violet',
    'legends-z-a':                 'Legends: Z-A',
    'champions':                   'Pokemon Champions',
}

BASE_URL = 'https://pokemondb.net/{slug}/gymleaders-elitefour'

# Headings that indicate a new trainer role section
ROLE_PATTERNS = [
    (re.compile(r'gym\s+leader', re.I),              'Gym Leader'),
    (re.compile(r'elite\s+four', re.I),              'Elite Four'),
    (re.compile(r'\bchampion\b', re.I),              'Champion'),
    (re.compile(r'team\s+star', re.I),               'Team Star Boss'),
    (re.compile(r'island\s+kahuna', re.I),           'Island Kahuna'),
    (re.compile(r'trial\s+captain', re.I),           'Trial Captain'),
    (re.compile(r'grand\s+trial', re.I),             'Grand Trial'),
    (re.compile(r'rival', re.I),                     'Rival'),
    (re.compile(r'frontier\s+brain', re.I),          'Frontier Brain'),
    (re.compile(r'team\s+(rocket|magma|aqua|galactic|plasma|flare|skull|yell|star)', re.I), 'Team Boss'),
    (re.compile(r'syndicate', re.I),                 'Syndicate Leader'),
]

# Battle variant labels found in sub-headings
VARIANT_PATTERNS = [
    (re.compile(r'rematch', re.I),           'Rematch'),
    (re.compile(r'second\s+battle', re.I),   'Rematch'),
    (re.compile(r'round\s+2', re.I),         'Rematch'),
    (re.compile(r'post.?game', re.I),        'Post-game'),
    (re.compile(r'champion\s+title', re.I),  'Champion Title'),
]


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _classify_role(text):
    for pattern, role in ROLE_PATTERNS:
        if pattern.search(text):
            return role
    return None


def _classify_variant(text):
    for pattern, variant in VARIANT_PATTERNS:
        if pattern.search(text):
            return variant
    return None


def _parse_level(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


class PokemonDbTrainersSpider(scrapy.Spider):
    """
    Scrapes gym leaders, elite four, champions, and equivalent trainer data
    from pokemondb.net/{game}/gymleaders-elitefour for all main-series games.
    """

    name = "pokemondb_trainers"
    allowed_domains = ["pokemondb.net"]

    def start_requests(self):
        for slug, game_name in GAME_PAGES.items():
            yield scrapy.Request(
                url=BASE_URL.format(slug=slug),
                callback=self.parse_page,
                cb_kwargs={'game': game_name},
                errback=self.handle_error,
            )

    def handle_error(self, failure):
        self.logger.warning(f"Failed to fetch: {failure.request.url}")

    def parse_page(self, response, game):
        """
        pokemondb trainer pages are structured as:
          h2  → role section (e.g. "Gym Leaders", "Elite Four", "Champion")
          h3  → individual trainer name (or sub-variant like "Rematch")
          div → trainer card with type badge and team table
        """
        current_role = None
        current_variant = 'First Battle'

        # Walk all significant block-level elements in document order
        for el in response.xpath(
            '//main//*[self::h2 or self::h3 or self::h4 '
            'or self::div[contains(@class,"trainer")] '
            'or self::div[contains(@class,"col")] '
            'or self::section]'
        ):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag == 'h2':
                role = _classify_role(text)
                if role:
                    current_role = role
                variant = _classify_variant(text)
                current_variant = variant if variant else 'First Battle'

            elif tag in ('h3', 'h4'):
                variant = _classify_variant(text)
                if variant:
                    current_variant = variant

        # Main parsing pass: find trainer blocks
        # pokemondb uses a consistent pattern of trainer name + type badge + team table
        yield from self._parse_trainer_blocks(response, game, current_role)

    def _parse_trainer_blocks(self, response, game, fallback_role):
        """
        Attempt to extract trainer data from the page.

        pokemondb trainer pages typically use one of two layouts:
        1. h3 with trainer name → div with type badge → table with Pokemon team
        2. Tabbed sections where each tab is a trainer

        We walk h3 headings and collect the nearest following sibling table.
        """
        current_role = fallback_role
        current_variant = 'First Battle'

        # Collect all h2/h3 + their associated content by walking siblings
        main = response.css('main, article, #main-content, .col-xl-9').get('')

        # Parse using the full DOM: iterate headings and capture trainer cards
        for section_h2 in response.css('h2'):
            h2_text = _clean(section_h2.css('::text').get(''))
            role = _classify_role(h2_text)
            if role:
                current_role = role
            variant = _classify_variant(h2_text)
            if variant:
                current_variant = variant
            else:
                current_variant = 'First Battle'

        # Now find each trainer block — look for trainer name headings (h3)
        # followed by a team table. pokemondb wraps each in a div.grid-col or similar.
        for trainer_section in response.css('div.grid-col, div.trainer-info, div.col-md-6, div.col-lg-4'):
            yield from self._extract_trainer_from_div(trainer_section, game, current_role, current_variant)

        # Fallback: if the above finds nothing, try a flat h3+table walk
        if not self._found_any:
            yield from self._walk_h3_table(response, game)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._found_any = False

    def _extract_trainer_from_div(self, div, game, role, variant):
        # Trainer name: h3 or strong or any heading inside the div
        name = _clean(div.css('h3::text, h4::text, strong.trainer-name::text').get(''))
        if not name:
            return

        # Specialty type: type badge link inside the div
        specialty = _clean(div.css('a.type-icon::text, span.type-icon::text, a[href*="/type/"]::text').get(''))

        # Location: small text or subtitle
        location = _clean(div.css('small::text, p.location::text').get(''))

        self._found_any = True
        yield TrainerItem(
            name=name,
            game=game,
            role=role,
            specialty_type=specialty or None,
            location=location or None,
            battle_variant=variant,
        )

        yield from self._parse_team_table(div, name, game, variant)

    def _walk_h3_table(self, response, game):
        """
        Fallback: walk h3 headings paired with following-sibling tables.
        This covers pages where trainers aren't wrapped in individual divs.
        """
        current_role = None
        current_variant = 'First Battle'

        for el in response.xpath('//main//*[self::h2 or self::h3 or self::table]'):
            tag = el.xpath('name()').get('')
            text = _clean(' '.join(el.xpath('.//text()').getall()))

            if tag == 'h2':
                role = _classify_role(text)
                if role:
                    current_role = role
                variant = _classify_variant(text)
                current_variant = variant if variant else 'First Battle'

            elif tag == 'h3':
                variant = _classify_variant(text)
                if variant:
                    current_variant = variant
                    continue

                # h3 is likely a trainer name
                specialty = _clean(
                    el.xpath('following-sibling::*[1][self::p or self::div]//a[contains(@href,"/type/")]//text()').get('')
                )
                location = _clean(
                    el.xpath('following-sibling::*[1][self::p or self::small]//text()').get('')
                )

                self._found_any = True
                yield TrainerItem(
                    name=text,
                    game=game,
                    role=current_role,
                    specialty_type=specialty or None,
                    location=location or None,
                    battle_variant=current_variant,
                )

                # The team table should be the next sibling table
                next_table = el.xpath('following-sibling::table[1]')
                if next_table:
                    yield from self._parse_team_table(next_table, text, game, current_variant)

            elif tag == 'table':
                pass  # handled above via h3 look-ahead

    def _parse_team_table(self, context, trainer_name, game, battle_variant):
        """
        Extract Pokemon from a team table within `context` (a Selector).

        pokemondb team tables typically have columns:
          Pokemon | Level | [Held Item] | [Ability] | Move | Move | Move | Move
        """
        for table in context.css('table.trainer-table, table.data-table, table'):
            headers = [_clean(th) for th in table.css('thead th::text, tr:first-child th::text').getall()]

            # Determine column indices
            held_col = next((i for i, h in enumerate(headers) if 'held' in h.lower() or 'item' in h.lower()), None)
            ability_col = next((i for i, h in enumerate(headers) if 'ability' in h.lower()), None)
            move_cols = [i for i, h in enumerate(headers) if 'move' in h.lower()]
            level_col = next((i for i, h in enumerate(headers) if 'level' in h.lower() or 'lv' in h.lower()), None)

            for team_order, row in enumerate(table.css('tbody tr')):
                cells = row.css('td')
                if not cells:
                    continue

                # Pokemon name: first link with ent-name class, or first cell text
                pokemon_name = _clean(row.css('a.ent-name::text').get(''))
                if not pokemon_name:
                    pokemon_name = _clean(cells[0].css('::text').get(''))
                if not pokemon_name:
                    continue

                # Level
                level = None
                if level_col is not None and level_col < len(cells):
                    level = _parse_level(cells[level_col].css('::text').get(''))
                elif len(cells) > 1:
                    # Try second cell as level if no explicit column
                    level = _parse_level(cells[1].css('::text').get(''))

                # Held item
                held_item = None
                if held_col is not None and held_col < len(cells):
                    held_item = _clean(cells[held_col].css('::text').get('')) or None

                # Ability
                ability = None
                if ability_col is not None and ability_col < len(cells):
                    ability = _clean(cells[ability_col].css('::text').get('')) or None

                # Moves
                moves = []
                for mc in move_cols:
                    if mc < len(cells):
                        move = _clean(cells[mc].css('::text').get(''))
                        if move and move.lower() not in ('—', '-', ''):
                            moves.append(move)

                yield TrainerPokemonItem(
                    trainer_name=trainer_name,
                    game=game,
                    battle_variant=battle_variant,
                    pokemon_name=pokemon_name,
                    level=level,
                    held_item=held_item,
                    ability=ability,
                    moves=moves if moves else None,
                    team_order=team_order,
                )
