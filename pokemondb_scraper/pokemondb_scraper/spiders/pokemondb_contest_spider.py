import re
import scrapy
from pokemondb_scraper.items import ContestStatItem

CONTEST_TYPES = ['Cool', 'Beautiful', 'Cute', 'Tough', 'Smart']


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_int(text):
    m = re.search(r'(\d+)', text or '')
    return int(m.group(1)) if m else None


class PokemonDbContestSpider(scrapy.Spider):
    """
    Scrapes contest condition stats (Cool/Beautiful/Cute/Tough/Smart appeal and jam)
    from pokemondb.net/move/all contest view, or from individual move pages.

    Contest stats appear in Gen 3 and 4 games.
    """

    name = "pokemondb_contest"
    allowed_domains = ["pokemondb.net"]
    # The contest stats per move page lists appeal/jam per contest type
    start_urls = ["https://pokemondb.net/move/all"]

    def parse(self, response):
        # Contest conditions are on individual move pages in a vitals table.
        # The move list gives us all move links; we visit each for contest data.
        for row in response.css('table#moves tbody tr'):
            href = row.css('td a::attr(href)').get('')
            name = _clean(row.css('td a::text').get(''))
            if href and name:
                yield response.follow(href, callback=self.parse_move_page, cb_kwargs={'move_name': name})

    def parse_move_page(self, response, move_name):
        """Extract contest type (appeal/jam) from individual move page."""
        vitals = {}
        for row in response.css('table.vitals-table tr'):
            th = _clean(' '.join(row.css('th ::text').getall()))
            td = _clean(' '.join(row.css('td ::text').getall()))
            if th and td:
                vitals[th.lower()] = td

        # Contest type is a row like "Contest type: Cool" with appeal and jam values
        contest_type = vitals.get('contest type', vitals.get('appeal type', ''))
        appeal = _parse_int(vitals.get('appeal', vitals.get('appeal points', '')))
        jam = _parse_int(vitals.get('jam', vitals.get('jam points', '')))

        if not contest_type or not contest_type.strip():
            return

        # Normalize to known contest types
        for ct in CONTEST_TYPES:
            if ct.lower() in contest_type.lower():
                contest_type = ct
                break

        # Contest stats are per move, not per Pokemon — store with move as pokemon_name field
        # (The ContestStatItem is designed for Pokemon, but moves also have contest types)
        # We use the move name as a proxy — API can join on moves table
        if appeal is not None or jam is not None:
            yield ContestStatItem(
                pokemon_name=move_name,   # move name, not Pokemon name (stored in same table)
                contest_type=contest_type,
                appeal=appeal,
                jam=jam,
            )
