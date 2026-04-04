import re
import scrapy
from pokemondb_scraper.items import GameItemDetail


def parse_price(text):
    """Extract integer price from strings like '₽300', '300', '1,000'. Returns None for free/N/A."""
    if not text:
        return None
    # Remove currency symbols, commas, whitespace
    cleaned = re.sub(r'[₽,\s]', '', text.strip())
    # A single dash or 'Can\'t be sold' type text → None
    if not cleaned or cleaned in ('-', '—', '–'):
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


class PokemonDbItemsSpider(scrapy.Spider):
    name = "pokemondb_items"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/item/all"]

    def parse(self, response):
        for row in response.css('table.data-table tbody tr'):
            cells = row.css('td')
            if len(cells) < 3:
                continue
            name     = cells[0].css('a::text').get('').strip()
            href     = cells[0].css('a::attr(href)').get('')
            category = cells[1].css('::text').get('').strip()
            effect   = cells[2].css('::text').get('').strip()
            if not name:
                continue

            sprite_name = name.lower().replace(' ', '-').replace("'", '')

            if href:
                yield response.follow(
                    href,
                    callback=self.parse_item,
                    cb_kwargs={
                        'name':       name,
                        'category':   category,
                        'effect':     effect,
                        'sprite_url': f'https://img.pokemondb.net/sprites/items/{sprite_name}.png',
                    },
                )
            else:
                yield GameItemDetail(
                    name=name,
                    category=category,
                    effect=effect,
                    sprite_url=f'https://img.pokemondb.net/sprites/items/{sprite_name}.png',
                    buy_price=None,
                    sell_price=None,
                )

    def parse_item(self, response, name, category, effect, sprite_url):
        """Extract buy/sell prices from the individual item page."""
        vitals = {}
        for row in response.xpath('//table[has-class("vitals-table")]//tbody/tr'):
            key   = ' '.join(row.xpath('./th//text()').getall()).strip()
            value = ' '.join(row.xpath('./td//text()').getall()).strip()
            if key:
                vitals[key] = value

        buy_price  = parse_price(vitals.get('Buy', '') or vitals.get('Buying price', '') or vitals.get('Cost', ''))
        sell_price = parse_price(vitals.get('Sell', '') or vitals.get('Selling price', ''))

        yield GameItemDetail(
            name=name,
            category=category,
            effect=effect,
            sprite_url=sprite_url,
            buy_price=buy_price,
            sell_price=sell_price,
        )
