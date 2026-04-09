import re
import scrapy
from pokemondb_scraper.items import PokemonGoItem


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_int(text):
    if not text:
        return None
    m = re.search(r'(\d+)', text.replace(',', ''))
    return int(m.group(1)) if m else None


class PokemonDbGoSpider(scrapy.Spider):
    """
    Scrapes Pokemon GO specific stats from pokemondb.net/pokemon/go.

    Yields PokemonGoItem for each Pokemon with GO base stats, max CP,
    buddy distance, and shiny/shadow availability.
    """

    name = "pokemondb_go"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/pokemon/go"]

    def parse(self, response):
        # The GO page has a large table with all Pokemon
        # Columns typically: #, Name, Max CP, Atk, Def, Sta, Buddy, Shiny, Shadow
        table = response.css('table#pokemon-go-table, table.data-table, table')
        if not table:
            return

        table = table[0]
        headers = [_clean(th) for th in table.css('thead th::text, thead th a::text').getall()]
        col = {}
        for i, h in enumerate(headers):
            col[h.lower()] = i

        for row in table.css('tbody tr'):
            cells = row.css('td')
            if not cells:
                continue

            # Pokemon name
            name = _clean(row.css('a.ent-name::text').get(''))
            if not name:
                # Try first cell
                name = _clean(cells[1].css('a::text, ::text').get('') if len(cells) > 1 else '')
            if not name:
                continue

            def get(key, *aliases):
                for k in (key, *aliases):
                    idx = col.get(k)
                    if idx is not None and idx < len(cells):
                        return _clean(' '.join(cells[idx].css('::text').getall()))
                return ''

            max_cp = _parse_int(get('max cp', 'cp'))
            base_attack = _parse_int(get('atk', 'attack', 'base attack'))
            base_defense = _parse_int(get('def', 'defense', 'base defense'))
            base_stamina = _parse_int(get('sta', 'stamina', 'hp', 'base stamina'))

            buddy_raw = get('buddy', 'buddy distance', 'buddy km')
            buddy_distance_km = _parse_int(buddy_raw)

            # Shiny / shadow availability — often indicated by a checkmark icon or "Yes"/"No" text
            shiny_raw = get('shiny').lower()
            shiny_available = bool(shiny_raw and shiny_raw not in ('no', '✗', '×', ''))

            shadow_raw = get('shadow').lower()
            shadow_available = bool(shadow_raw and shadow_raw not in ('no', '✗', '×', ''))

            yield PokemonGoItem(
                pokemon_name=name,
                max_cp=max_cp,
                buddy_distance_km=buddy_distance_km,
                base_attack=base_attack,
                base_defense=base_defense,
                base_stamina=base_stamina,
                shiny_available=shiny_available,
                shadow_available=shadow_available,
            )
