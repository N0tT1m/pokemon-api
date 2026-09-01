import scrapy

import re

from pokemondb_scraper.items import (
    PokemonItem,
    TypeDefenseItem,
    EvolutionItem,
    MoveItem,
    LocationItem,
    GameNationalDexItem,
    PokedexEntryItem,
    PokemonNameItem,
    PokemonSpriteItem,
    PokemonFormItem,
    EggMovePokemonItem,
)

# Unicode fraction → float mapping for type defense values
FRACTION_MAP = {
    '0':  0.0,
    '½':  0.5,
    '¼':  0.25,
    '2':  2.0,
    '4':  4.0,
    '1':  1.0,
}

# Stat key normalization from the HTML table headers
STAT_KEYS = {
    'HP':      'hp',
    'Attack':  'attack',
    'Defense': 'defense',
    'Sp. Atk': 'sp_atk',
    'Sp. Def': 'sp_def',
    'Speed':   'speed',
    'Total':   'total',
}


def parse_int(value):
    """Parse a string to int, returning None for dashes or empty strings."""
    if not value:
        return None
    cleaned = value.strip().replace('—', '').replace('–', '').replace('-', '')
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


# Values pokemondb uses for "no data" in a vitals row.
BLANK_VITALS = {"", "-", "\u2014", "\u2013", "N/A"}


class PokemonDbAllPokemon(scrapy.Spider):
    name = "pokemondb_pokemon"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def parse(self, response):
        seen = set()
        for cell in response.css('table#pokedex tbody tr td.cell-name'):
            name = cell.css('a.ent-name::text').get('')
            href = cell.css('a.ent-name::attr(href)').get('')
            if name and href and name not in seen:
                seen.add(name)
                yield response.follow(href, callback=self.parse_pokemon)

    def _parse_card(self, card):
        """Extract Pokemon info from an infocard div."""
        return {
            'number': card.xpath('.//small[1]/text()').get('').strip(),
            'name': card.xpath('.//a[has-class("ent-name")]/text()').get('').strip(),
            'url': card.xpath('.//a[has-class("ent-name")]/@href').get('').strip(),
            'types': card.xpath('.//small[2]/a/text()').getall(),
        }

    def _parse_arrow(self, arrow):
        """Extract evolution method text from an infocard-arrow span."""
        # Get all text content including link text, e.g. "(use Tart Apple)"
        texts = arrow.xpath('.//small//text()').getall()
        return ' '.join(t.strip() for t in texts).strip().strip('()')

    def _walk_evo_tree(self, evo_list_node, pokemon_name, parent_name, counter):
        """
        Recursively walk a div.infocard-list-evo node.

        Structure:
          div.infocard-list-evo
            div.infocard              (a Pokemon card)
            span.infocard-arrow       (arrow with method text) 
            div.infocard              (next Pokemon card)   
            span.infocard-evo-split   (contains branches)
              div.infocard-list-evo   (branch 1: arrow + card + ...)
              div.infocard-list-evo   (branch 2: arrow + card + ...)
        """
        # Direct child elements (cards, arrows, split containers)
        children = evo_list_node.xpath('./*')

        pending_arrow = None  # the most recent arrow text before a card
        last_card_name = parent_name  # tracks the "from" Pokemon for the next card

        for child in children:
            tag = child.xpath('name()').get('')
            classes = child.xpath('@class').get('')

            if 'infocard-arrow' in classes:
                # This is an arrow — save the method text for the next card
                pending_arrow = self._parse_arrow(child)

            elif 'infocard-evo-split' in classes:
                # Branch container — each child div.infocard-list-evo is a separate branch
                for branch in child.xpath('./div[has-class("infocard-list-evo")]'):
                    yield from self._walk_evo_tree(branch, pokemon_name, last_card_name, counter)

            elif tag == 'div' and 'infocard' in classes and 'infocard-arrow' not in classes:
                # This is a Pokemon card
                info = self._parse_card(child)
                if not info['name']:
                    continue

                evolves_from = last_card_name
                evolves_via = pending_arrow
                pending_arrow = None

                order = counter[0]
                counter[0] += 1

                yield EvolutionItem(
                    pokemon_name=pokemon_name,
                    number=info['number'],
                    evo_name=info['name'],
                    evo_url=info['url'],
                    types=info['types'],
                    evolves_via=evolves_via,
                    evolves_from=evolves_from,
                    chain_order=order,
                )

                last_card_name = info['name']

    def parse_pokemon(self, response):
        pokemon_name = response.css('main h1::text').get('').strip()
        if not pokemon_name:
            return

        # --- Vitals tables ---
        vitals = {}
        for section in response.xpath('//h2[following-sibling::table[has-class("vitals-table")]]'):
            header = section.xpath('./text()').get('').strip()
            table = section.xpath('./following-sibling::table[has-class("vitals-table")][1]')
            for row in table.xpath('.//tbody/tr'):
                # Collapse whitespace rather than plain-joining the text nodes.
                # A header split across an element -- pokemondb writes
                # "<th>Base <a ...>Friendship</a></th>" -- yields ['Base ',
                # 'Friendship'], which a naive ' '.join turns into the
                # double-spaced 'Base  Friendship', silently missing every
                # vitals.get('Base Friendship') lookup below.
                key = ' '.join(' '.join(row.xpath('./th//text()').getall()).split())
                value = ' '.join(' '.join(row.xpath('./td//text()').getall()).split())
                if not key:
                    continue
                # A page carries one vitals table per form, and a later form can
                # leave a row blank -- pokemondb writes an em dash for Gender on
                # several alternate forms. A plain assignment lets that placeholder
                # overwrite the base form's real value, which made 23 species
                # (Dragonite, Skarmory, Froslass, Pyroar, ...) report as
                # genderless. Never let a blank overwrite something real.
                if value in BLANK_VITALS and key in vitals:
                    continue
                vitals[key] = value

        # --- Base stats table ---
        # The table is inside a div.resp-scroll wrapper, not a direct sibling of the h2
        stats = {}
        for row in response.xpath('//h2[contains(text(),"Base stats")]/following-sibling::div[1]//table[1]//tbody/tr'):
            key = row.xpath('./th/text()').get('').strip()
            cells = [c.strip() for c in row.xpath('./td//text()').getall() if c.strip()]
            if key and cells:
                field = STAT_KEYS.get(key)
                if field:
                    stats[field] = parse_int(cells[0])

        # --- Abilities (parsed individually from the HTML) ---
        abilities = []
        ability_td = response.xpath(
            '//table[has-class("vitals-table")]//th[contains(text(),"Abilities")]/following-sibling::td[1]'
        )
        for link in ability_td.xpath('.//a'):
            ability_name = link.xpath('./text()').get('').strip()
            if ability_name:
                # Check if this link's parent small has "(hidden ability)" text
                parent_text = ' '.join(link.xpath('./parent::*//text()').getall())
                if 'hidden ability' in parent_text.lower():
                    ability_name += ' (Hidden)'
                abilities.append(ability_name)

        item = PokemonItem(
            name=pokemon_name,
            url=response.url,
            national_no=vitals.get('National №', ''),
            types=vitals.get('Type', '').split(),
            species=vitals.get('Species', ''),
            height=vitals.get('Height', ''),
            weight=vitals.get('Weight', ''),
            abilities=abilities,
            ev_yield=vitals.get('EV yield', ''),
            catch_rate=vitals.get('Catch rate', ''),
            base_friendship=vitals.get('Base Friendship', ''),
            base_exp=vitals.get('Base Exp.', ''),
            growth_rate=vitals.get('Growth Rate', ''),
            egg_groups=[g.strip() for g in vitals.get('Egg Groups', '').split(',')],
            gender_ratio=vitals.get('Gender', ''),
            egg_cycles=vitals.get('Egg cycles', ''),
            hp=stats.get('hp'),
            attack=stats.get('attack'),
            defense=stats.get('defense'),
            sp_atk=stats.get('sp_atk'),
            sp_def=stats.get('sp_def'),
            speed=stats.get('speed'),
            total=stats.get('total'),
        )
        yield item

        # --- Alternate forms (Mega, regional variants, forme differences) ---
        # pokemondb uses a tab panel per form inside div.tabset-basics.
        # Tab links: a.tabs-tab[href="#tab-basic-N"] → panel: div.tabs-panel#tab-basic-N
        tab_links = response.css('div.tabset-basics a.tabs-tab')
        tab_panels = response.css('div.tabset-basics div.tabs-panel')
        if len(tab_panels) > 1:
            for tab_link, panel in zip(tab_links, tab_panels):
                form_name = tab_link.css('::text').get('').strip()
                # Skip the base form (first tab) — already captured above
                if tab_link.css('.is-active') or tab_link.attrib.get('class', '').startswith('tabs-tab is-active'):
                    continue
                if not form_name or form_name == pokemon_name:
                    continue

                # Form vitals
                form_vitals = {}
                for row in panel.xpath('.//table[has-class("vitals-table")]//tbody/tr'):
                    key   = ' '.join(row.xpath('./th//text()').getall()).strip()
                    value = ' '.join(row.xpath('./td//text()').getall()).strip()
                    if key:
                        form_vitals[key] = value

                # Form abilities
                form_abilities = []
                ability_td = panel.xpath(
                    './/table[has-class("vitals-table")]//th[contains(text(),"Abilities")]/following-sibling::td[1]'
                )
                for link in ability_td.xpath('.//a'):
                    aname = link.xpath('./text()').get('').strip()
                    if aname:
                        parent_text = ' '.join(link.xpath('./parent::*//text()').getall())
                        if 'hidden ability' in parent_text.lower():
                            aname += ' (Hidden)'
                        form_abilities.append(aname)

                # Form base stats (any tr whose th is a known stat key)
                form_stats = {}
                for row in panel.xpath('.//tbody/tr'):
                    key = row.xpath('./th/text()').get('').strip()
                    cells = [c.strip() for c in row.xpath('./td//text()').getall() if c.strip()]
                    if key in STAT_KEYS and cells:
                        form_stats[STAT_KEYS[key]] = parse_int(cells[0])

                if not form_vitals and not form_stats:
                    continue  # Empty panel — skip

                form_types_raw = form_vitals.get('Type', '') or vitals.get('Type', '')
                yield PokemonFormItem(
                    pokemon_name=pokemon_name,
                    form_name=form_name,
                    types=form_types_raw.split() if form_types_raw else [],
                    abilities=form_abilities or abilities,
                    height=form_vitals.get('Height', '') or vitals.get('Height', ''),
                    weight=form_vitals.get('Weight', '') or vitals.get('Weight', ''),
                    hp=form_stats.get('hp'),
                    attack=form_stats.get('attack'),
                    defense=form_stats.get('defense'),
                    sp_atk=form_stats.get('sp_atk'),
                    sp_def=form_stats.get('sp_def'),
                    speed=form_stats.get('speed'),
                    total=form_stats.get('total'),
                )

        # --- Type defenses ---
        for cell in response.xpath('//table[has-class("type-table")]//tr[td]//td'):
            type_name = cell.xpath('./@title').get('').split('\u2192')[0].strip()
            raw_value = cell.xpath('./text()').get('1').strip()
            if type_name:
                yield TypeDefenseItem(
                    pokemon_name=pokemon_name,
                    type_name=type_name,
                    multiplier=FRACTION_MAP.get(raw_value, 1.0),
                )

        # --- Evolution chain (recursive tree walk) ---
        evo_root = response.xpath('//div[has-class("infocard-list-evo")][1]')
        if evo_root:
            evo_counter = [0]  # mutable counter for chain_order
            for evo_item in self._walk_evo_tree(evo_root, pokemon_name, None, evo_counter):
                yield evo_item

        # --- Locations (dl/dt/dd structure) ---
        location_dl = response.xpath('//h2[contains(text(),"Where to find")]/following-sibling::div[1]//dl | //h2[contains(text(),"Where to find")]/following-sibling::dl[1]')
        if not location_dl:
            location_dl = response.xpath('//h2[contains(text(),"Where to find")]/following-sibling::*[self::dl or self::div][1]//dl | //h2[contains(text(),"Where to find")]/following-sibling::dl[1]')
        for dt in location_dl.xpath('./dt'):
            games_raw = dt.xpath('.//text()').getall()
            games = [g.strip() for g in games_raw if g.strip()]
            dd = dt.xpath('./following-sibling::dd[1]')
            location_links = dd.xpath('.//a/text()').getall()
            location_text = dd.xpath('.//text()').getall()
            location_text = ' '.join(t.strip() for t in location_text).strip()

            # Skip "Not available" or "Location data not yet available"
            if 'not available' in location_text.lower() or 'not yet available' in location_text.lower():
                continue

            locations = [loc.strip() for loc in location_links if loc.strip()] if location_links else [location_text]
            if games and locations:
                yield LocationItem(
                    pokemon_name=pokemon_name,
                    games=games,
                    locations=locations,
                )

        # --- Moves (inside tabbed sections) ---
        # Moves are inside tab panels; parse all h3 + table pairs across all tabs
        move_sections = {
            'Moves learnt by level up': 'level-up',
            'Moves learnt by TM': 'tm',
            'Egg moves': 'egg',
            'Move Tutor moves': 'tutor',
            'Moves learnt by TR': 'tm',
        }
        for h3 in response.xpath('//h3'):
            header_text = h3.xpath('.//text()').get('').strip()
            learn_method = None
            for pattern, method in move_sections.items():
                if pattern in header_text:
                    learn_method = method
                    break
            if not learn_method:
                continue

            # The table may be a direct sibling or inside a resp-scroll div
            table = h3.xpath('./following-sibling::div[1]//table | ./following-sibling::table[1]')
            if not table:
                continue

            is_egg_or_tutor = learn_method in ('egg', 'tutor')
            last_egg_move = None  # track move name for parent rows
            for row in table.xpath('.//tbody/tr'):
                cells = row.xpath('./td')
                if not cells:
                    continue

                if is_egg_or_tutor:
                    # Detect parent-pokemon rows: a single td[colspan] containing ent-name links
                    if len(cells) == 1 and cells[0].xpath('./@colspan'):
                        if learn_method == 'egg' and last_egg_move:
                            for parent_link in cells[0].xpath('.//a[has-class("ent-name")]'):
                                parent_name = parent_link.xpath('./text()').get('').strip()
                                if parent_name:
                                    yield EggMovePokemonItem(
                                        pokemon_name=pokemon_name,
                                        move_name=last_egg_move,
                                        parent_name=parent_name,
                                    )
                        continue

                    move_name = cells[0].xpath('.//a[has-class("ent-name")]/text()').get('')
                    if not move_name:
                        move_name = cells[0].xpath('.//a/text()').get('')
                    move_type = cells[1].xpath('.//a/text()').get('') if len(cells) > 1 else ''
                    category = cells[2].xpath('.//img/@alt').get('') if len(cells) > 2 else ''
                    if not category:
                        category = cells[2].xpath('.//text()').get('') if len(cells) > 2 else ''
                    power = parse_int(cells[3].xpath('.//text()').get('')) if len(cells) > 3 else None
                    accuracy = parse_int(cells[4].xpath('.//text()').get('')) if len(cells) > 4 else None
                    move_name = (move_name or '').strip()
                    if move_name and learn_method == 'egg':
                        last_egg_move = move_name
                    yield MoveItem(
                        pokemon_name=pokemon_name,
                        learn_method=learn_method,
                        level_or_tm='—',
                        move_name=move_name,
                        type=(move_type or '').strip(),
                        category=(category or '').strip(),
                        power=power,
                        accuracy=accuracy,
                    )
                else:
                    level_or_tm = cells[0].xpath('.//text()').get('') if cells else ''
                    move_name = cells[1].xpath('.//a[has-class("ent-name")]/text()').get('') if len(cells) > 1 else ''
                    if not move_name:
                        move_name = cells[1].xpath('.//a/text()').get('') if len(cells) > 1 else ''
                    move_type = cells[2].xpath('.//a/text()').get('') if len(cells) > 2 else ''
                    category = cells[3].xpath('.//img/@alt').get('') if len(cells) > 3 else ''
                    if not category:
                        category = cells[3].xpath('.//text()').get('') if len(cells) > 3 else ''
                    power = parse_int(cells[4].xpath('.//text()').get('')) if len(cells) > 4 else None
                    accuracy = parse_int(cells[5].xpath('.//text()').get('')) if len(cells) > 5 else None
                    yield MoveItem(
                        pokemon_name=pokemon_name,
                        learn_method=learn_method,
                        level_or_tm=(level_or_tm or '').strip(),
                        move_name=(move_name or '').strip(),
                        type=(move_type or '').strip(),
                        category=(category or '').strip(),
                        power=power,
                        accuracy=accuracy,
                    )

        # --- Pokedex entries (flavor text) ---
        # Structure: h2 "Pokédex entries" -> h3 (form) -> div.resp-scroll > table.vitals-table
        #   Each row: th > span.igame (game names) | td.cell-med-text (flavor text)
        for h3 in response.xpath('//h2[contains(text(),"dex entries")]/following-sibling::h3'):
            # Stop if we hit the next h2
            next_h2 = h3.xpath('./following-sibling::h2[1]')
            table = h3.xpath('./following-sibling::div[1]//table[has-class("vitals-table")]')
            if not table:
                table = h3.xpath('./following-sibling::table[has-class("vitals-table")][1]')
            for row in table.xpath('.//tbody/tr'):
                game_spans = row.xpath('./th//span[has-class("igame")]/text()').getall()
                flavor_text = row.xpath('./td[has-class("cell-med-text")]//text()').get('').strip()
                if flavor_text:
                    for game_name in game_spans:
                        game_name = game_name.strip()
                        if game_name:
                            yield PokedexEntryItem(
                                pokemon_name=pokemon_name,
                                game_version=game_name,
                                flavor_text=flavor_text,
                            )

        # --- Multi-language names ---
        # Structure: h2 "Other languages" -> div > table.vitals-table
        #   Each row: th (language) | td (localized name)
        # Take only the first vitals-table after "Other languages" (names, not species names)
        names_table = response.xpath(
            '//h2[contains(text(),"Other languages")]/following-sibling::div[1]//table[has-class("vitals-table")][1]'
        )
        for row in names_table.xpath('.//tbody/tr'):
            language = row.xpath('./th/text()').get('').strip()
            localized = row.xpath('./td//text()').get('').strip()
            if language and localized:
                yield PokemonNameItem(
                    pokemon_name=pokemon_name,
                    language=language,
                    localized_name=localized,
                )

        # --- Sprites ---
        # Structure: table.sprites-history-table
        #   thead: th = "Type", "Generation 1", "Generation 2", ...
        #   tbody: each tr: td[0] = sprite type (Normal/Shiny), td[1..N] = img per generation
        sprites_table = response.xpath('//table[has-class("sprites-history-table")]')
        gen_headers = sprites_table.xpath('.//thead/tr/th/text()').getall()
        for row in sprites_table.xpath('.//tbody/tr'):
            cells = row.xpath('./td')
            sprite_type = cells[0].xpath('.//b/text()').get('').strip().lower() if cells else ''
            if not sprite_type:
                sprite_type = cells[0].xpath('.//text()').get('').strip().lower() if cells else ''
            for i, cell in enumerate(cells[1:], start=1):
                img_url = cell.xpath('.//img/@src').get('')
                if img_url:
                    gen_name = gen_headers[i] if i < len(gen_headers) else ''
                    yield PokemonSpriteItem(
                        pokemon_name=pokemon_name,
                        sprite_type=sprite_type,
                        generation=gen_name.strip() if gen_name else None,
                        url=img_url,
                    )

        # --- Game national dex (from "Local №" row) ---
        # Format: "0025 " <small class="text-muted">(Yellow/Red/Blue)</small><br>
        # Number is a bare text node, game name is inside <small>
        national_no = parse_int(vitals.get('National №', ''))
        if national_no:
            local_td = response.xpath(
                '//table[has-class("vitals-table")]//th[contains(text(),"Local")]/following-sibling::td[1]'
            )
            # Get the full inner HTML and parse number + game pairs
            all_text_nodes = local_td.xpath('./text()').getall()
            all_small_nodes = local_td.xpath('./small/text()').getall()
            for i, num_text in enumerate(all_text_nodes):
                num_text = num_text.strip()
                local_no = parse_int(num_text)
                if local_no is not None and i < len(all_small_nodes):
                    game_str = all_small_nodes[i].strip().strip('()')
                    # Remove em-dash suffixes like "X/Y — Central Kalos"
                    if '\u2014' in game_str:
                        game_str = game_str.split('\u2014')[0].strip()
                    if game_str:
                        yield GameNationalDexItem(
                            game=game_str,
                            pokemon_name=pokemon_name,
                            national_no=national_no,
                    )
