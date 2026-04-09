import re
import scrapy
from pokemondb_scraper.items import MoveDetail

# Generation ranges by national dex number of the first move introduced that gen
# pokemondb lists generation as "Introduced in Generation X"
GEN_MOVE_PATTERN = re.compile(r'generation\s+([IVX]+|\d+)', re.I)

ROMAN_TO_INT = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9}


def parse_int(value):
    if not value:
        return None
    cleaned = value.strip().replace('—', '').replace('–', '').replace('∞', '')
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


def parse_generation(text):
    """Parse 'Generation I', 'Generation IV', or 'Generation 4' to int."""
    if not text:
        return None
    m = GEN_MOVE_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(1).upper()
    if raw in ROMAN_TO_INT:
        return ROMAN_TO_INT[raw]
    try:
        return int(raw)
    except ValueError:
        return None


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
        """Extract priority, target, generation, flags, contest type, and Z/Max move data."""
        vitals = {}
        for row in response.xpath('//table[has-class("vitals-table")]//tbody/tr'):
            key   = ' '.join(row.xpath('./th//text()').getall()).strip()
            value = ' '.join(row.xpath('./td//text()').getall()).strip()
            if key:
                vitals[key] = value

        priority = parse_priority(vitals.get('Priority', ''))
        target   = vitals.get('Target', '').strip() or None

        # Generation introduced — often in a "Introduced in" or "Generation" vitals row
        gen_raw = vitals.get('Introduced in', '') or vitals.get('Generation', '')
        generation_introduced = parse_generation(gen_raw)
        # Fallback: check page title or breadcrumb text
        if not generation_introduced:
            page_text = ' '.join(response.css('main *::text').getall()[:20])
            generation_introduced = parse_generation(page_text)

        # Move flags — pokemondb lists them in a "Flags" row or as a list of spans
        flags = []
        flags_td = response.xpath(
            '//table[has-class("vitals-table")]//th[contains(text(),"Flag")]/following-sibling::td[1]'
        )
        if flags_td:
            for flag in flags_td.xpath('.//li/text() | .//span/text() | .//a/text()').getall():
                f = flag.strip()
                if f and f not in flags:
                    flags.append(f)

        # Contest type — e.g. "Cool", "Cute", etc.
        contest_type = vitals.get('Contest type', '') or vitals.get('Appeal type', '') or None
        if contest_type:
            contest_type = contest_type.strip() or None

        # Z-Move equivalent — "Makes the user use [Z-Move name]" style text
        z_move_equivalent = None
        z_raw = vitals.get('Z-Move', '') or vitals.get('Z-Crystal', '')
        if z_raw:
            z_move_equivalent = z_raw.strip() or None
        if not z_move_equivalent:
            # Try to find Z-Move link on the page
            z_link = response.css('a[href*="/move/"][href*="z-"]:not([href="/move/all"])::text').get('')
            if z_link:
                z_move_equivalent = z_link.strip() or None

        # Max Move equivalent (Dynamax)
        max_move_equivalent = None
        max_raw = vitals.get('Max Move', '') or vitals.get('Dynamax Move', '')
        if max_raw:
            max_move_equivalent = max_raw.strip() or None

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
            generation_introduced=generation_introduced,
            z_move_equivalent=z_move_equivalent,
            max_move_equivalent=max_move_equivalent,
            contest_type=contest_type,
            flags=flags if flags else None,
        )
