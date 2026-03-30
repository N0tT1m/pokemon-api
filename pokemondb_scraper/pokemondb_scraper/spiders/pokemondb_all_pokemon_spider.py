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
                key = ' '.join(row.xpath('./th//text()').getall()).strip()
                value = ' '.join(row.xpath('./td//text()').getall()).strip()
                if key:
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

        # --- Locations ---
        for row in response.xpath('//h2[contains(text(),"Where to find")]/following-sibling::table[1]//tbody/tr[th and td]'):
            games = row.xpath('./th//span/text()').getall()
            location_links = row.xpath('./td//a[@href]/text()').getall()
            location_text = row.xpath('./td//small/text()').get('')

            yield LocationItem(
                pokemon_name=pokemon_name,
                games=[g.strip() for g in games],
                locations=location_links if location_links else [location_text.strip()],
            )

        # --- Moves: level-up ---
        for row in response.xpath(
            '//h3[contains(text(),"Moves learnt by level up")]/following-sibling::table[1]//tbody/tr'
        ):
            yield MoveItem(
                pokemon_name=pokemon_name,
                learn_method='level-up',
                level_or_tm=row.xpath('./td[1]//text()').get('').strip(),
                move_name=row.xpath('./td[2]//a[@class="ent-name"]/text()').get('').strip(),
                type=row.xpath('./td[3]//a/text()').get('').strip(),
                category=row.xpath('./td[4]//img/@alt').get('').strip(),
                power=parse_int(row.xpath('./td[5]/text()').get('')),
                accuracy=parse_int(row.xpath('./td[6]/text()').get('')),
            )

        # --- Moves: TM ---
        for row in response.xpath(
            '//h3[contains(text(),"Moves learnt by TM")]/following-sibling::table[1]//tbody/tr'
        ):
            yield MoveItem(
                pokemon_name=pokemon_name,
                learn_method='tm',
                level_or_tm=row.xpath('./td[1]//text()').get('').strip(),
                move_name=row.xpath('./td[2]//a[@class="ent-name"]/text()').get('').strip(),
                type=row.xpath('./td[3]//a/text()').get('').strip(),
                category=row.xpath('./td[4]//img/@alt').get('').strip(),
                power=parse_int(row.xpath('./td[5]/text()').get('')),
                accuracy=parse_int(row.xpath('./td[6]/text()').get('')),
            )

        # --- Moves: Egg moves ---
        for row in response.xpath(
            '//h3[contains(text(),"Egg moves")]/following-sibling::table[1]//tbody/tr'
        ):
            yield MoveItem(
                pokemon_name=pokemon_name,
                learn_method='egg',
                level_or_tm='—',
                move_name=row.xpath('./td[1]//a[@class="ent-name"]/text()').get('').strip(),
                type=row.xpath('./td[2]//a/text()').get('').strip(),
                category=row.xpath('./td[3]//img/@alt').get('').strip(),
                power=parse_int(row.xpath('./td[4]/text()').get('')),
                accuracy=parse_int(row.xpath('./td[5]/text()').get('')),
            )

        # --- Moves: Move Tutor ---
        for row in response.xpath(
            '//h3[contains(text(),"Move Tutor moves")]/following-sibling::table[1]//tbody/tr'
        ):
            yield MoveItem(
                pokemon_name=pokemon_name,
                learn_method='tutor',
                level_or_tm='—',
                move_name=row.xpath('./td[1]//a[@class="ent-name"]/text()').get('').strip(),
                type=row.xpath('./td[2]//a/text()').get('').strip(),
                category=row.xpath('./td[3]//img/@alt').get('').strip(),
                power=parse_int(row.xpath('./td[4]/text()').get('')),
                accuracy=parse_int(row.xpath('./td[5]/text()').get('')),
            )

        # --- Pokedex entries (flavor text) ---
        for row in response.xpath('//h2[contains(text(),"Pok")][contains(text(),"dex entries")]/following-sibling::table[1]//tbody/tr'):
            game_names = row.xpath('./th//text()').getall()
            flavor_text = ' '.join(row.xpath('./td//text()').getall()).strip()
            if game_names and flavor_text:
                for game_name in game_names:
                    game_name = game_name.strip()
                    if game_name:
                        yield PokedexEntryItem(
                            pokemon_name=pokemon_name,
                            game_version=game_name,
                            flavor_text=flavor_text,
                        )

        # --- Multi-language names ---
        for row in response.xpath('//h2[contains(text(),"Other languages")]/following-sibling::table[1]//tbody/tr'):
            language = row.xpath('./th/text()').get('').strip()
            localized = row.xpath('./td[1]/text()').get('').strip()
            if language and localized:
                yield PokemonNameItem(
                    pokemon_name=pokemon_name,
                    language=language,
                    localized_name=localized,
                )

        # --- Sprites ---
        for sprite_section in response.xpath('//h2[contains(text(),"Sprites")]/following-sibling::*'):
            tag = sprite_section.xpath('name()').get('')
            if tag == 'h2':
                break  # Next section
            # Look for generation headers and sprite images
            gen_name = sprite_section.xpath('.//h3/text()').get('')
            for img in sprite_section.xpath('.//img/@src').getall():
                if 'sprites' in img or 'artwork' in img:
                    sprite_type = 'normal'
                    if 'shiny' in img.lower():
                        sprite_type = 'shiny'
                    elif 'female' in img.lower():
                        sprite_type = 'female'
                    yield PokemonSpriteItem(
                        pokemon_name=pokemon_name,
                        sprite_type=sprite_type,
                        generation=gen_name.strip() if gen_name else None,
                        url=img,
                    )

        # --- Game national dex (from "Local №" row) ---
        # Each text node in the Local № td looks like "0025 (Red/Blue/Yellow)"
        national_no = parse_int(vitals.get('National №', ''))
        if national_no:
            local_td = response.xpath(
                '//table[has-class("vitals-table")]//th[contains(text(),"Local")]/following-sibling::td[1]'
            )
            for text_node in local_td.xpath('.//text()').getall():
                text_node = text_node.strip()
                match = re.match(r'\d+\s*\((.+)\)', text_node)
                if match:
                    game_str = match.group(1).strip()
                    # Split combined game names like "Red/Blue/Yellow"
                    # but keep compound names like "Brilliant Diamond/Shining Pearl" intact
                    # These are already individual entries per line on pokemondb
                    yield GameNationalDexItem(
                        game=game_str,
                        pokemon_name=pokemon_name,
                        national_no=national_no,
                    )
