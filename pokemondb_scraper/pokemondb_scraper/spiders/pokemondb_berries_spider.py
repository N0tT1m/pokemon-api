import re

import scrapy

from pokemondb_scraper.items import BerryItem, BerryFlavorItem


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_int(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


class PokemonDbBerriesSpider(scrapy.Spider):
    """
    Scrapes berry data from pokemondb.net/berry.

    Yields BerryItem and BerryFlavorItem for each berry.
    """

    name = "pokemondb_berries"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/berry"]

    def parse(self, response):
        # Berry pages on pokemondb list all berries in a table and link to individual pages
        for link in response.css('table a.ent-name::attr(href)').getall():
            yield response.follow(link, callback=self.parse_berry)

        # If there's no table of berries with links, try parsing the page directly
        # (pokemondb may list all berries inline)
        if not response.css('table a.ent-name'):
            yield from self._parse_berry_table(response)

    def parse_berry(self, response):
        yield from self._parse_berry_page(response)

    def _parse_berry_page(self, response):
        """Parse an individual berry detail page."""
        name = _clean(response.css('main h1::text').get(''))
        if not name:
            return

        # Remove " Berry" suffix if present for storage (optional, keep full name)
        # pokemondb stores as "Cheri Berry" — keep as-is

        # Vitals table: rows with th → td pairs
        vitals = {}
        for row in response.css('table.vitals-table tr'):
            th = _clean(row.css('th::text').get(''))
            td = _clean(' '.join(row.css('td ::text, td::text').getall()))
            if th and td:
                vitals[th.lower()] = td

        # Natural Gift data
        natural_gift_type = None
        natural_gift_power = None
        if 'natural gift' in vitals:
            ng = vitals['natural gift']
            # Format is usually "Fire · 80" or "Fire (80)"
            m = re.match(r'(\w+)[^\d]*(\d+)', ng)
            if m:
                natural_gift_type = m.group(1)
                natural_gift_power = int(m.group(2))
        # Also try separate rows
        if 'natural gift type' in vitals:
            natural_gift_type = vitals['natural gift type']
        if 'natural gift power' in vitals:
            natural_gift_power = _parse_int(vitals['natural gift power'])

        size_mm = _parse_int(vitals.get('size', '') or vitals.get('size (mm)', ''))
        firmness = vitals.get('firmness')
        growth_time = _parse_int(vitals.get('growth time', '') or vitals.get('hours to grow', ''))

        # Effect / description — look for p tags in main content
        effect = None
        for p in response.css('main p'):
            text = _clean(' '.join(p.css('::text').getall()))
            if text and len(text) > 20:
                effect = text
                break

        yield BerryItem(
            name=name,
            natural_gift_type=natural_gift_type,
            natural_gift_power=natural_gift_power,
            size_mm=size_mm,
            firmness=firmness,
            effect=effect,
            growth_time=growth_time,
        )

        # Flavor potency table — rows: Spicy | Dry | Sweet | Bitter | Sour
        for row in response.css('table.flavor-table tr, table tr'):
            cells = row.css('td')
            header = _clean(row.css('th::text').get(''))
            if not cells or not header:
                continue
            flavor_names = ['Spicy', 'Dry', 'Sweet', 'Bitter', 'Sour']
            if header.lower() in ('spicy', 'dry', 'sweet', 'bitter', 'sour'):
                potency = _parse_int(_clean(' '.join(cells[0].css('::text').getall())))
                if potency is not None:
                    yield BerryFlavorItem(
                        berry_name=name,
                        flavor=header,
                        potency=potency,
                    )
            # Alternatively: flavors listed in columns with header row
            elif header.lower() == 'flavor' or not header:
                flavor_values = [_clean(' '.join(c.css('::text').getall())) for c in cells]
                for flavor, value in zip(flavor_names, flavor_values):
                    potency = _parse_int(value)
                    if potency is not None:
                        yield BerryFlavorItem(
                            berry_name=name,
                            flavor=flavor,
                            potency=potency,
                        )

    def _parse_berry_table(self, response):
        """
        Fallback: parse a page that lists all berries in a table inline
        (rather than linking to individual pages).
        """
        # Find table headers to determine column indices
        headers = [_clean(th) for th in response.css('table thead th::text').getall()]
        if not headers:
            return

        col = {h.lower(): i for i, h in enumerate(headers)}

        for row in response.css('table tbody tr'):
            cells = row.css('td')
            if not cells:
                continue

            name_cell = cells[col.get('berry', col.get('name', 0))] if col else cells[0]
            name = _clean(name_cell.css('a::text, ::text').get(''))
            if not name:
                continue

            def get_cell(key, *aliases):
                for k in (key, *aliases):
                    idx = col.get(k)
                    if idx is not None and idx < len(cells):
                        return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            ng_raw = get_cell('natural gift', 'natural gift power')
            m = re.match(r'(\w+)[^\d]*(\d+)', ng_raw)
            natural_gift_type = m.group(1) if m else None
            natural_gift_power = int(m.group(2)) if m else _parse_int(ng_raw)

            yield BerryItem(
                name=name,
                natural_gift_type=natural_gift_type,
                natural_gift_power=natural_gift_power,
                size_mm=_parse_int(get_cell('size', 'size (mm)')),
                firmness=get_cell('firmness') or None,
                effect=get_cell('effect') or None,
                growth_time=_parse_int(get_cell('growth time')),
            )

            for flavor in ('Spicy', 'Dry', 'Sweet', 'Bitter', 'Sour'):
                potency = _parse_int(get_cell(flavor.lower()))
                if potency is not None:
                    yield BerryFlavorItem(
                        berry_name=name,
                        flavor=flavor,
                        potency=potency,
                    )
