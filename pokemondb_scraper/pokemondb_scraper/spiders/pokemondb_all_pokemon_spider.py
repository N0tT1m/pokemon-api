from pathlib import Path

import scrapy
import pandas as pd


class PokemonDbAllPokemon(scrapy.Spider):
    name = "pokemondb_pokemon"
    allowed_domains = ["pokemondb.net"]
    target_word = "/pokedex/"
    base_url = "https://pokemondb.net"
    pokemon_urls = []
    tm_moves = []
    locations = []
    level_moves = []
    data = {}
    type_defenses = {}
    evolution_chain = []
    evolutions = []

    async def start(self):
        urls = ["https://pokemondb.net/pokedex/all"]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        for next_page in response.css('a::attr(href)').getall():
            if self.target_word in next_page:
                url = self.base_url + next_page
                self.pokemon_urls.append(url)
        for url in self.pokemon_urls:
            yield scrapy.Request(url=url, callback=self.parse_pokemon)
        
    def parse_pokemon(self, response):
        # Find each h2 and the table that follows it
        for section in response.xpath('//h2[following-sibling::table[has-class("vitals-table")]]'):
            header = section.xpath('./text()').get('').strip()
            table = section.xpath('./following-sibling::table[has-class("vitals-table")][1]')
            
            rows = {}
            for row in table.xpath('.//tbody/tr'):
                key = row.xpath('./th//text()').getall()
                key = ' '.join(k.strip() for k in key).strip()
                value = ' '.join(row.xpath('./td//text()').getall()).strip()
                if key:
                    rows[key] = value
            
            self.data[header] = rows

        for row in table.xpath('.//tbody/tr[not(parent::tfoot)]'):
            key = row.xpath('./th/text()').get('').strip()
            cells = [c.strip() for c in row.xpath('./td//text()').getall() if c.strip()]
            if key and cells:
                rows[key] = {
                    'base': cells[0],
                    'min': cells[1] if len(cells) > 1 else None,
                    'max': cells[2] if len(cells) > 2 else None,
                }

        for cell in response.xpath('//table[has-class("type-table")]//tr[td]//td'):
            type_name = cell.xpath('./@title').get('').split('→')[0].strip()
            value = cell.xpath('./text()').get('1').strip()  # empty cell = 1x
            if type_name:
                self.type_defenses[type_name] = value

        arrow_texts = response.xpath('//div[has-class("infocard-list-evo")]//span[has-class("infocard-arrow")]//small/text()').getall()

        for card in response.xpath('//div[has-class("infocard-list-evo")]/div[has-class("infocard")]'):
            self.evolutions.append({
                'number': card.xpath('.//small[1]/text()').get('').strip(),
                'name':   card.xpath('.//a[has-class("ent-name")]/text()').get('').strip(),
                'url':    card.xpath('.//a[has-class("ent-name")]/@href').get('').strip(),
                'types':  card.xpath('.//small[2]/a/text()').getall(),
            })

        # Zip evolutions with the arrows between them
        for i, evo in enumerate(self.evolutions):
            if i < len(arrow_texts):
                evo['evolves_via'] = arrow_texts[i].strip('()')
            else:
                evo['evolves_via'] = None
            self.evolution_chain.append(evo)

        for row in response.xpath('//table//tbody/tr[th and td]'):
            games = row.xpath('./th//span/text()').getall()
            location_links = row.xpath('./td//a[@href]/text()').getall()
            location_text = row.xpath('./td//small/text()').get('')  # fallback text

            self.locations.append({
                'games': [g.strip() for g in games],
                'locations': location_links if location_links else [location_text.strip()],
            })

        # TM moves — table whose first header is "TM"
        for row in response.xpath('//table[has-class("data-table")][.//th[contains(., "TM")]]//tbody/tr'):
            self.tm_moves.append({
                'tm':       row.xpath('./td[1]//text()').get('').strip(),
                'name':     row.xpath('./td[2]//a[@class="ent-name"]/text()').get('').strip(),
                'type':     row.xpath('./td[3]//a/text()').get('').strip(),
                'category': row.xpath('./td[4]//img/@alt').get('').strip(),
                'power':    row.xpath('./td[5]/text()').get('').strip(),
                'accuracy': row.xpath('./td[6]/text()').get('').strip(),
            })

        for row in response.xpath('//table[has-class("data-table")]//tbody/tr'):
            first_cell = row.xpath('./td[1]')
            is_tm = bool(first_cell.xpath('./a').get())

            move = {
                'learn_method': 'tm' if is_tm else 'level-up',
                'level_or_tm': first_cell.xpath('.//text()').get('').strip(),
                'name': row.xpath('./td[2]//a[@class="ent-name"]/text()').get('').strip(),
                'type': row.xpath('./td[3]//a/text()').get('').strip(),
                'category': row.xpath('./td[4]//img/@alt').get('').strip(),
                'power': row.xpath('./td[5]/text()').get('').strip(),
                'accuracy': row.xpath('./td[6]/text()').get('').strip(),
            }
            self.level_moves.append(move)

    tm_moves_df = pd.DataFrame(tm_moves)
    locations_df = pd.DataFrame(locations)
    level_moves_df = pd.DataFrame(level_moves)
    data_df = pd.DataFrame(data)
    type_defenses_df = pd.DataFrame(type_defenses)
    evolution_chain_df = pd.DataFrame(evolution_chain)
    evolutions_df = pd.DataFrame(evolutions)

    dfs = [tm_moves_df, locations_df, level_moves_df, data_df, type_defenses_df, evolution_chain_df, evolutions_df]
    dfs.to_csv('combined.csv', index=False)
