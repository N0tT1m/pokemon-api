import scrapy
from pokemondb_scraper.items import MoveDetail


def parse_int(value):
    if not value:
        return None
    cleaned = value.strip().replace('—', '').replace('–', '').replace('-', '').replace('∞', '')
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


class PokemonDbMovesSpider(scrapy.Spider):
    name = "pokemondb_moves"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/move/all"]

    def parse(self, response):
        for row in response.css('table#moves tbody tr'):
            cells = row.css('td')
            if len(cells) < 8:
                continue
            name = cells[0].css('a::text').get('').strip()
            move_type = cells[1].css('a::text').get('').strip()
            category = cells[2].css('img::attr(alt)').get('').strip()
            power = parse_int(cells[3].css('::text').get(''))
            accuracy = parse_int(cells[4].css('::text').get(''))
            pp = parse_int(cells[5].css('::text').get(''))
            effect = cells[6].css('::text').get('').strip()
            prob = parse_int(cells[7].css('::text').get(''))

            if name:
                yield MoveDetail(
                    name=name,
                    type=move_type,
                    category=category,
                    power=power,
                    accuracy=accuracy,
                    pp=pp,
                    effect=effect,
                    effect_chance=prob,
                )
