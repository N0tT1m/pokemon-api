import scrapy
from pokemondb_scraper.items import LocationEncounterItem

REGIONS = {
    'kanto': 'Kanto',
    'johto': 'Johto',
    'hoenn': 'Hoenn',
    'sinnoh': 'Sinnoh',
    'unova': 'Unova',
    'kalos': 'Kalos',
    'alola': 'Alola',
    'galar': 'Galar',
    'hisui': 'Hisui',
    'paldea': 'Paldea',
}


class PokemonDbLocationsSpider(scrapy.Spider):
    name = "pokemondb_locations"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/location"]

    def parse(self, response):
        # Location links are inside tab panels: div#loc-{region}
        for region_slug, region_name in REGIONS.items():
            panel = response.css(f'div#loc-{region_slug}')
            if not panel:
                # Fallback: find links by href pattern
                pass
            for link in panel.css(f'a[href^="/location/{region_slug}-"]::attr(href)').getall():
                yield response.follow(
                    link,
                    callback=self.parse_location,
                    cb_kwargs={'region': region_name},
                )
            # Also try global fallback
            if not panel:
                for link in response.xpath(f'//a[contains(@href, "/location/{region_slug}-")]/@href').getall():
                    yield response.follow(
                        link,
                        callback=self.parse_location,
                        cb_kwargs={'region': region_name},
                    )

    def parse_location(self, response, region):
        # Get actual location name from page title
        title = response.css('main h1::text').get('')
        if not title:
            title = response.css('h1::text').get('')
        route_name = title.strip().split(',')[0].strip() if title else 'Unknown'

        # Parse encounter tables organized by generation (h2) and method (h3)
        # Structure: h2 (generation) -> h3 (method) -> div.resp-scroll > table.data-table
        current_method = None

        for element in response.xpath('//main//*[self::h2 or self::h3 or self::table[has-class("data-table")] or self::div[contains(@class,"resp-scroll")]]'):
            tag = element.xpath('name()').get('')

            if tag == 'h3':
                current_method = element.xpath('.//text()').get('').strip()
            elif tag == 'h2':
                # Reset method on new generation section
                current_method = None
            elif tag == 'div' or tag == 'table':
                # Get the table (may be inside resp-scroll div)
                if tag == 'div':
                    table = element.xpath('.//table[has-class("data-table")]')
                else:
                    table = element

                if not table:
                    continue

                # Check for sub-encounter labels in multi-tbody tables
                for tbody in table.xpath('.//tbody'):
                    sub_method = tbody.xpath('.//th[has-class("cell-loc-status")]/text()').get('')
                    effective_method = sub_method.strip() if sub_method and sub_method.strip() else current_method

                    for row in tbody.xpath('./tr'):
                        # Skip spacer and status header rows
                        if row.xpath('.//th[has-class("cell-loc-spacer") or has-class("cell-loc-status")]'):
                            continue

                        pokemon_name = row.css('a.ent-name::text').get('')
                        if not pokemon_name:
                            pokemon_name = row.xpath('.//td[1]//a/text()').get('')
                        if not pokemon_name:
                            continue

                        # Games: non-blank game cells only
                        games = row.css('td.cell-loc-game:not(.cell-loc-game-blank)::text').getall()
                        games = [g.strip() for g in games if g.strip()]

                        # Skip rows where all game cells are blank
                        if not games:
                            continue

                        # Rarity: try percentage badge first (newer gens use span.icon-rarity),
                        # then fall back to icon-loc alt text in non-cell-fixed tds
                        # (older gens use icon images like "Common", "Uncommon", "Rare").
                        # We must skip cell-fixed tds since those hold time-of-day icons
                        # (Morning/Day/Night) which share the same icon-loc class.
                        rarity = row.css('span.icon-rarity::text').get('')
                        if not rarity:
                            rarity_img = row.xpath(
                                './/td[not(contains(@class,"cell-fixed"))]'
                                '//img[has-class("icon-loc")]/@alt'
                            ).get('')
                            if rarity_img and rarity_img.strip().lower() not in ('morning', 'day', 'night'):
                                rarity = rarity_img.strip()

                        # Levels: look for cell-num td that's not the rarity
                        level_range = ''
                        num_cells = row.css('td.cell-num')
                        for cell in num_cells:
                            text = cell.xpath('.//text()').get('').strip()
                            # Skip rarity cells (they contain span.icon-rarity)
                            if cell.css('span.icon-rarity'):
                                continue
                            if text and text != rarity:
                                level_range = text
                                break

                        # Time of day
                        time_imgs = row.xpath('.//td[contains(@class,"cell-fixed")]//img[has-class("icon-loc")]/@alt').getall()
                        time_of_day = ', '.join(t.strip() for t in time_imgs if t.strip()) if time_imgs else None

                        yield LocationEncounterItem(
                            region=region,
                            route_name=route_name,
                            pokemon_name=pokemon_name.strip(),
                            games=games if games else [],
                            encounter_method=effective_method if effective_method else None,
                            rarity=rarity.strip() if rarity else None,
                            level_range=level_range if level_range else None,
                            time_of_day=time_of_day,
                        )
