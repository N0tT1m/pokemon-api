import scrapy
from pokemondb_scraper.items import NatureItem


class PokemonDbNaturesSpider(scrapy.Spider):
    name = "pokemondb_natures"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/mechanics/natures"]

    def parse(self, response):
        for row in response.css('table.data-table tbody tr'):
            cells = row.css('td')
            if len(cells) < 3:
                continue
            name = cells[0].css('::text').get('').strip()
            increased = cells[1].css('::text').get('').strip()
            decreased = cells[2].css('::text').get('').strip()

            if name:
                # Neutral natures show '—' for stats
                if increased in ('—', '-', ''):
                    increased = None
                if decreased in ('—', '-', ''):
                    decreased = None

                yield NatureItem(
                    name=name,
                    increased_stat=increased,
                    decreased_stat=decreased,
                )
