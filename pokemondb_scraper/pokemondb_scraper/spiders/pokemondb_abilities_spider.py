import scrapy
from pokemondb_scraper.items import AbilityDetail, AbilityPokemonItem


def parse_int(value):
    if not value:
        return None
    cleaned = value.strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


class PokemonDbAbilitiesSpider(scrapy.Spider):
    name = "pokemondb_abilities"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/ability"]

    def parse(self, response):
        for row in response.css('table.data-table tbody tr'):
            cells = row.css('td')
            if len(cells) < 4:
                continue
            name = cells[0].css('a::text').get('').strip()
            description = cells[2].css('::text').get('').strip()
            gen = parse_int(cells[3].css('::text').get(''))
            href = cells[0].css('a::attr(href)').get('')

            if name:
                yield AbilityDetail(
                    name=name,
                    description=description,
                    generation=gen,
                )
                if href:
                    yield response.follow(href, callback=self.parse_ability_pokemon, cb_kwargs={'ability_name': name})

    def parse_ability_pokemon(self, response, ability_name):
        for card in response.css('div.infocard'):
            pokemon_name = card.css('a.ent-name::text').get('').strip()
            if not pokemon_name:
                continue
            # Check if this is listed under "Hidden ability" section
            parent_h2 = card.xpath('./preceding::h2[1]/text()').get('')
            is_hidden = 'hidden' in parent_h2.lower()

            yield AbilityPokemonItem(
                ability_name=ability_name,
                pokemon_name=pokemon_name,
                is_hidden=is_hidden,
            )
