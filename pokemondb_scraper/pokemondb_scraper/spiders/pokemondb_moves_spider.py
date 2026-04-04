import re
import scrapy
from pokemondb_scraper.items import MoveDetail


def parse_int(value):
    if not value:
        return None
    cleaned = value.strip().replace('—', '').replace('–', '').replace('∞', '')
    # A lone dash (used as "N/A") should return None
    if cleaned in ('-', ''):
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_priority(value):
    """Handle priority values like '+1', '0', '-6 (Switching out)'."""
    if not value:
        return None
    m = re.search(r'([+-]?\d+)', value)
    return int(m.group(1)) if m else None


class PokemonDbMovesSpider(scrapy.Spider):
    name = "pokemondb_moves"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/move/all"]

    def parse(self, response):
        """Discover all move links from the list; pass basic data to individual page callback."""
        for row in response.css('table#moves tbody tr'):
            cells = row.css('td')
            if len(cells) < 8:
                continue
            name = cells[0].css('a::text').get('').strip()
            href = cells[0].css('a::attr(href)').get('')
            if not name or not href:
                continue

            move_type = cells[1].css('a::text').get('').strip()
            category  = cells[2].css('img::attr(alt)').get('').strip()
            power     = parse_int(cells[3].css('::text').get(''))
            accuracy  = parse_int(cells[4].css('::text').get(''))
            pp        = parse_int(cells[5].css('::text').get(''))
            effect    = cells[6].css('::text').get('').strip()
            prob      = parse_int(cells[7].css('::text').get(''))

            yield response.follow(
                href,
                callback=self.parse_move,
                cb_kwargs={
                    'name':          name,
                    'move_type':     move_type,
                    'category':      category,
                    'power':         power,
                    'accuracy':      accuracy,
                    'pp':            pp,
                    'effect':        effect,
                    'effect_chance': prob,
                },
            )

    def parse_move(self, response, name, move_type, category, power, accuracy, pp, effect, effect_chance):
        """Extract priority and target from the individual move page."""
        vitals = {}
        for row in response.xpath('//table[has-class("vitals-table")]//tbody/tr'):
            key   = ' '.join(row.xpath('./th//text()').getall()).strip()
            value = ' '.join(row.xpath('./td//text()').getall()).strip()
            if key:
                vitals[key] = value

        priority = parse_priority(vitals.get('Priority', ''))
        target   = vitals.get('Target', '').strip() or None

        yield MoveDetail(
            name=name,
            type=move_type,
            category=category,
            power=power,
            accuracy=accuracy,
            pp=pp,
            effect=effect,
            effect_chance=effect_chance,
            priority=priority,
            target=target,
        )
