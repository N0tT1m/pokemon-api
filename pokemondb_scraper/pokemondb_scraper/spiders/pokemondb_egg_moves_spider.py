import scrapy
from pokemondb_scraper.items import EggMovePokemonItem


class PokemonDbEggMovesSpider(scrapy.Spider):
    """
    Scrapes egg move parent data from the gen-8 learnset pages on pokemondb.net.

    Gen 9 egg-move-parents sections are JavaScript-rendered and not available
    in static HTML; gen 8 is the most recent generation with static parent
    tables.  For pokemon introduced in gen 9 the gen-8 page simply has no
    egg-move data, so they are skipped silently.

    URL pattern:  https://pokemondb.net/pokedex/{slug}/moves/8
    Anchor:       id="egg-move-parents"
    Per-move:     h3[id^="eggmove--"]  →  a.infocard in following table
    """

    name = "pokemondb_egg_moves"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/pokedex/all"]

    def parse(self, response):
        seen = set()
        for cell in response.css('table#pokedex tbody tr td.cell-name'):
            href = cell.css('a.ent-name::attr(href)').get('')
            if not href:
                continue
            slug = href.rstrip('/').split('/')[-1]
            if not slug or slug in seen:
                continue
            seen.add(slug)
            pokemon_name = cell.css('a.ent-name::text').get('').strip()
            yield response.follow(
                f'/pokedex/{slug}/moves/8',
                callback=self.parse_learnset,
                cb_kwargs={'pokemon_name': pokemon_name},
            )

    def parse_learnset(self, response, pokemon_name):
        # The egg-move-parents section is anchored by id="egg-move-parents".
        # If absent (gen-9-only pokemon, or no egg moves), nothing to do.
        if not response.xpath('//*[@id="egg-move-parents"]'):
            return

        # Each egg move has an h3 whose id starts with "eggmove--".
        for h3 in response.xpath('//*[starts-with(@id, "eggmove--")]'):
            move_name = h3.css('::text').get('').strip()
            if not move_name:
                continue

            # The parent table is inside a div.resp-scroll sibling of the h3.
            table = h3.xpath(
                './following-sibling::div[contains(@class,"resp-scroll")][1]//table'
                ' | ./following-sibling::table[1]'
            )
            if not table:
                continue

            # Each tbody row: td[0] = how parents learn the move,
            #                 td[1] = infocard links for compatible parents.
            seen_parents = set()
            for row in table.xpath('.//tbody/tr'):
                cells = row.xpath('./td')
                if len(cells) < 2:
                    continue
                for link in cells[1].xpath('.//a[contains(@class,"infocard")]'):
                    # Text after <br> is the pokemon name.
                    parts = [t.strip() for t in link.xpath('./text()').getall() if t.strip()]
                    parent_name = ' '.join(parts)
                    if parent_name and parent_name not in seen_parents:
                        seen_parents.add(parent_name)
                        yield EggMovePokemonItem(
                            pokemon_name=pokemon_name,
                            move_name=move_name,
                            parent_name=parent_name,
                        )
