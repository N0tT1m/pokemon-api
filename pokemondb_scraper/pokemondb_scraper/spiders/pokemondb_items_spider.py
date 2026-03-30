import scrapy
from pokemondb_scraper.items import GameItemDetail

class PokemonDbItemsSpider(scrapy.Spider):
    name = "pokemondb_items"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/item/all"]

    def parse(self, response):
        for row in response.css('table.data-table tbody tr'):
            cells = row.css('td')
            if len(cells) < 3:
                continue
            name = cells[0].css('a::text').get('').strip()
            category = cells[1].css('::text').get('').strip()
            effect = cells[2].css('::text').get('').strip()
            if name:
                sprite_name = name.lower().replace(' ', '-').replace("'", '')
                yield GameItemDetail(
                    name=name,
                    category=category,
                    effect=effect,
                    sprite_url=f'https://img.pokemondb.net/sprites/items/{sprite_name}.png',
                )
