import re
import scrapy
from pokemondb_scraper.items import ZMoveItem


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_int(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


class PokemonDbZMovesSpider(scrapy.Spider):
    """
    Scrapes Z-Move data from pokemondb.net/mechanic/z-moves.

    Yields ZMoveItem for each Z-Move including its base move, type, power,
    category, and effect.
    """

    name = "pokemondb_zmoves"
    allowed_domains = ["pokemondb.net"]
    start_urls = [
        "https://pokemondb.net/mechanic/z-moves",
        "https://pokemondb.net/move/all",  # supplement: Z-Moves also appear in move list
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen = set()

    def parse(self, response):
        if 'z-moves' in response.url:
            yield from self._parse_zmoves_page(response)
        elif 'move/all' in response.url:
            yield from self._parse_move_list_for_zmoves(response)

    def _parse_zmoves_page(self, response):
        """Parse the dedicated Z-Moves mechanics page."""
        # Z-Moves are listed in tables with columns: Move, Type, Category, Power, Effect
        # There may be multiple tables (one for universal Z-Moves, one per type)
        for table in response.css('table.data-table, table.move-list'):
            headers = [_clean(th) for th in table.css('thead th::text').getall()]
            if not headers:
                continue

            col = {h.lower(): i for i, h in enumerate(headers)}

            for row in table.css('tbody tr'):
                cells = row.css('td')
                if not cells:
                    continue

                name_cell = col.get('move', col.get('z-move', 0))
                name = _clean(cells[name_cell].css('a::text, ::text').get('')) if name_cell < len(cells) else ''
                if not name or name in self._seen:
                    continue

                move_type = ''
                type_idx = col.get('type', col.get('z-type'))
                if type_idx is not None and type_idx < len(cells):
                    move_type = _clean(cells[type_idx].css('a::text, ::text').get(''))

                category = ''
                cat_idx = col.get('category', col.get('cat.'))
                if cat_idx is not None and cat_idx < len(cells):
                    category = _clean(cells[cat_idx].css('img::attr(alt), ::text').get(''))

                power = None
                pow_idx = col.get('power', col.get('pwr.'))
                if pow_idx is not None and pow_idx < len(cells):
                    power = _parse_int(cells[pow_idx].css('::text').get(''))

                effect = ''
                eff_idx = col.get('effect', col.get('description'))
                if eff_idx is not None and eff_idx < len(cells):
                    effect = _clean(' '.join(cells[eff_idx].css('::text').getall()))

                # Base move — often listed in a separate column or as a note
                base_move = None
                base_idx = col.get('base move', col.get('requires', col.get('move required')))
                if base_idx is not None and base_idx < len(cells):
                    base_move = _clean(cells[base_idx].css('a::text, ::text').get('')) or None

                self._seen.add(name)
                yield ZMoveItem(
                    name=name,
                    type=move_type or None,
                    power=power,
                    effect=effect or None,
                    base_move=base_move,
                    category=category or None,
                )

        # Also look for Z-Move info in description paragraphs
        # Universal Z-Moves and signature Z-Moves may be listed differently
        for section_h2 in response.css('h2, h3'):
            section_text = _clean(section_h2.css('::text').get(''))
            # Look for lists near type-specific Z-Move headings
            next_table = section_h2.xpath('following-sibling::table[1]')
            if not next_table:
                continue
            if 'z-move' not in section_text.lower() and 'type' not in section_text.lower():
                continue

            move_type_for_section = re.search(r'(\w+)\s+type', section_text, re.I)
            inferred_type = move_type_for_section.group(1) if move_type_for_section else None

            for row in next_table.css('tbody tr'):
                cells = row.css('td')
                if not cells:
                    continue
                name = _clean(cells[0].css('a::text, ::text').get(''))
                if not name or name in self._seen:
                    continue
                self._seen.add(name)
                yield ZMoveItem(
                    name=name,
                    type=inferred_type,
                    power=_parse_int(cells[2].css('::text').get('')) if len(cells) > 2 else None,
                    effect=_clean(' '.join(cells[-1].css('::text').getall())) if cells else None,
                    base_move=_clean(cells[1].css('a::text, ::text').get('')) if len(cells) > 1 else None,
                    category=None,
                )

    def _parse_move_list_for_zmoves(self, response):
        """Supplement: pull Z-Moves from the main move list (they're tagged as Z-Moves)."""
        for row in response.css('table#moves tbody tr'):
            cells = row.css('td')
            if len(cells) < 3:
                continue
            name = _clean(cells[0].css('a::text').get(''))
            # Z-Moves have "Z-Move" in their effect or a special icon
            effect = _clean(cells[6].css('::text').get('')) if len(cells) > 6 else ''
            row_text = _clean(' '.join(row.css('::text').getall()))
            if 'z-move' not in row_text.lower() and not name.startswith('Z-') and not name.endswith('-Move'):
                continue
            if name in self._seen:
                continue
            self._seen.add(name)

            move_type = _clean(cells[1].css('a::text').get(''))
            category = _clean(cells[2].css('img::attr(alt)').get(''))
            power = _parse_int(cells[3].css('::text').get('')) if len(cells) > 3 else None

            yield ZMoveItem(
                name=name,
                type=move_type or None,
                power=power,
                effect=effect or None,
                base_move=None,
                category=category or None,
            )
