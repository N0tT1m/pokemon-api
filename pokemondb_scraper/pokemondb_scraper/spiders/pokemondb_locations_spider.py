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
        # Find all location links grouped by region
        for region_slug, region_name in REGIONS.items():
            # Find the section for this region
            section = response.xpath(
                f'//h2[contains(translate(text(),"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"{region_slug}")]/following-sibling::*[1]'
            )
            if not section:
                # Try finding by class or just grab all links mentioning the region
                section = response.xpath(f'//a[contains(@href, "/location/{region_slug}")]')

            for link in response.xpath(f'//a[contains(@href, "/location/{region_slug}-")]/@href').getall():
                yield response.follow(
                    link,
                    callback=self.parse_location,
                    cb_kwargs={'region': region_name, 'route_name': link.split('/')[-1].replace(f'{region_slug}-', '').replace('-', ' ').title()},
                )

    def parse_location(self, response, region, route_name):
        # Get actual location name from page title
        title = response.css('main h1::text').get('')
        if title:
            route_name = title.strip()

        # Parse encounter tables - they have Pokemon cards organized by encounter method
        for section in response.xpath('//h3 | //h2'):
            method_text = section.xpath('.//text()').get('').strip()
            if not method_text:
                continue

            # The table following this header contains encounter data
            table = section.xpath('./following-sibling::table[1]')
            if not table:
                continue

            for row in table.xpath('.//tbody/tr'):
                pokemon_name = row.xpath('.//td[1]//a[has-class("ent-name")]/text()').get('')
                if not pokemon_name:
                    pokemon_name = row.xpath('.//td[1]//a/text()').get('').strip()
                if not pokemon_name:
                    continue

                games = row.xpath('.//td[1]//small/text()').getall()
                games = [g.strip() for g in games if g.strip()]

                # Rarity info
                rarity = row.xpath('.//td[last()]//text()').get('').strip()

                # Level range
                level_text = row.xpath('.//td[2]//text()').get('').strip()

                yield LocationEncounterItem(
                    region=region,
                    route_name=route_name,
                    pokemon_name=pokemon_name.strip(),
                    games=games if games else [],
                    encounter_method=method_text if method_text else None,
                    rarity=rarity if rarity else None,
                    level_range=level_text if level_text else None,
                    time_of_day=None,
                )
