import re
from datetime import datetime, timezone
import scrapy
from pokemondb_scraper.items import RaidEventItem, RaidCounterItem

# Matches article URLs that are likely Tera Raid guides
RAID_URL_PATTERN = re.compile(r'(tera.?raid|raid.?battle|\d+.?star)', re.I)
RAID_TITLE_PATTERN = re.compile(r'(tera.?raid|raid.?battle|\d+.?star|raid.?guide)', re.I)

# Headings that introduce a counters/recommended Pokemon section
COUNTER_HEADINGS = re.compile(
    r'(best|top|recommended|counters?|strong.against|weak.to|how.to.beat|how.to.win)',
    re.I,
)

# Known game8 SV raid category/index pages
START_URLS = [
    "https://game8.co/games/Pokemon-Scarlet-Violet/categories/3085",
    "https://game8.co/games/Pokemon-Scarlet-Violet/categories/3087",
    "https://game8.co/games/Pokemon-Scarlet-Violet/",
]


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _parse_star_rating(text):
    m = re.search(r'(\d+)[\-\u2011\s]*[Ss]tar', text)
    return int(m.group(1)) if m else None


def _extract_pokemon_name(title):
    """Pull just the Pokemon name from a title like 'Charizard 7-Star Tera Raid Battle Guide'."""
    # Remove everything from the star rating onwards
    name = re.sub(r'\s*\d+[\-\u2011\s]*[Ss]tar.*$', '', title)
    # Remove trailing Tera/Raid/Battle/Guide keywords
    name = re.sub(r'\s*(Tera|Raid|Battle|Guide|Event|Challenge).*$', '', name, flags=re.I)
    return _clean(name)


def _parse_date_range(text):
    """Return (start, end) strings from 'Jan 1, 2025 - Jan 7, 2025' style text."""
    text = _clean(text)
    parts = re.split(r'\s*[-\u2013\u2014~]\s*', text, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), None


# Formats game8 commonly uses for event dates.
_DATE_FORMATS = [
    '%B %d, %Y',      # January 1, 2025
    '%b %d, %Y',      # Jan 1, 2025
    '%B %d %Y',       # January 1 2025
    '%b %d %Y',       # Jan 1 2025
    '%m/%d/%Y',       # 01/01/2025
    '%Y-%m-%d',       # 2025-01-01
    '%d %B %Y',       # 1 January 2025
    '%d %b %Y',       # 1 Jan 2025
]


def _try_parse_date(text):
    """Try to parse a date string into a date object. Returns None on failure."""
    if not text:
        return None
    # Strip ordinal suffixes: 1st, 2nd, 3rd, 4th … 31st
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text.strip(), flags=re.I)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _is_active_from_dates(event_start, event_end):
    """
    Return True if today falls within [event_start, event_end].
    Returns None if dates cannot be parsed (caller should fall back).
    """
    start = _try_parse_date(event_start)
    if start is None:
        return None
    today = datetime.now(timezone.utc).date()
    if event_end:
        end = _try_parse_date(event_end)
        if end is None:
            return None
        return start <= today <= end
    # No end date: treat as active if start is in the past 60 days
    delta = (today - start).days
    return 0 <= delta <= 60


class Game8RaidsSpider(scrapy.Spider):
    """Scrapes Tera Raid event data and best counters from game8.co."""

    name = "game8_raids"
    allowed_domains = ["game8.co"]
    start_urls = START_URLS

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_urls = set()

    def parse(self, response):
        """Parse category/index pages and follow raid article links."""
        for a in response.css('a[href]'):
            href = a.attrib.get('href', '')
            link_text = _clean(' '.join(a.css('::text').getall()))
            if not href:
                continue
            full_url = response.urljoin(href)
            if full_url in self._seen_urls:
                continue
            if 'game8.co/games/Pokemon-Scarlet-Violet/archives/' not in full_url:
                continue
            if RAID_URL_PATTERN.search(href) or RAID_TITLE_PATTERN.search(link_text):
                self._seen_urls.add(full_url)
                yield scrapy.Request(full_url, callback=self.parse_raid_page)

        # Follow pagination
        for href in response.css('a.a-pagination__item::attr(href), a[rel="next"]::attr(href)').getall():
            full_url = response.urljoin(href)
            if full_url not in self._seen_urls:
                self._seen_urls.add(full_url)
                yield scrapy.Request(full_url, callback=self.parse)

    def parse_raid_page(self, response):
        """Parse an individual raid article page."""
        title = _clean(response.css('h1::text').get(''))
        if not title or not RAID_TITLE_PATTERN.search(title):
            return

        pokemon_name = _extract_pokemon_name(title)
        if not pokemon_name:
            return

        star_rating = _parse_star_rating(title)
        tera_type = None
        event_start = None
        event_end = None
        is_active = False

        # --- Parse overview/details tables for tera type and event dates ---
        for table in response.css('table'):
            for row in table.css('tr'):
                header = _clean(' '.join(row.css('th::text').getall())).lower()
                value = _clean(' '.join(row.css('td::text').getall()))
                if not header or not value:
                    continue

                if 'tera type' in header or 'tera-type' in header:
                    tera_type = value
                elif any(kw in header for kw in ('date', 'period', 'duration', 'schedule', 'available', 'time')):
                    event_start, event_end = _parse_date_range(value)
                elif 'star' in header and not star_rating:
                    star_rating = _parse_star_rating(value)

        # Determine is_active: prefer date-based calculation, fall back to page text
        active_from_dates = _is_active_from_dates(event_start, event_end)
        if active_from_dates is not None:
            is_active = active_from_dates
        else:
            body_text = _clean(' '.join(response.css('article *::text, .a-contentBlock *::text').getall())).lower()
            if re.search(r'currently\s+active|now\s+available|ongoing\s+event', body_text):
                is_active = True

        yield RaidEventItem(
            pokemon_name=pokemon_name,
            tera_type=tera_type,
            star_rating=star_rating,
            event_start=event_start,
            event_end=event_end,
            is_active=is_active,
            source_url=response.url,
        )

        # --- Parse best counters ---
        yield from self._parse_counters(response, pokemon_name, tera_type)

        # If this page links to a dedicated counters/guide sub-page, follow it
        for a in response.css('a[href]'):
            href = a.attrib.get('href', '')
            text = _clean(' '.join(a.css('::text').getall()))
            if COUNTER_HEADINGS.search(text) and 'archives' in href:
                full_url = response.urljoin(href)
                if full_url not in self._seen_urls:
                    self._seen_urls.add(full_url)
                    yield scrapy.Request(
                        full_url,
                        callback=self._parse_counter_subpage,
                        cb_kwargs={'pokemon_name': pokemon_name, 'tera_type': tera_type},
                    )

    def _parse_counter_subpage(self, response, pokemon_name, tera_type):
        yield from self._parse_counters(response, pokemon_name, tera_type)

    def _parse_counters(self, response, pokemon_name, tera_type):
        """
        Walk the page looking for a section headed by a counter/recommendation
        keyword and yield RaidCounterItem for each Pokemon found there.
        """
        in_section = False
        rank = 0

        for el in response.css('h2, h3, h4, table, ul, ol'):
            tag = el.root.tag

            if tag in ('h2', 'h3', 'h4'):
                heading_text = _clean(' '.join(el.css('::text').getall()))
                in_section = bool(COUNTER_HEADINGS.search(heading_text))
                if in_section:
                    rank = 0
                continue

            if not in_section:
                continue

            if tag == 'table':
                for row in el.css('tr'):
                    cells = row.css('td')
                    if not cells:
                        continue
                    # First cell is the Pokemon name (may be wrapped in a link)
                    name_cell = _clean(' '.join(cells[0].css('::text').getall()))
                    # Skip obvious header-like rows
                    if not name_cell or name_cell.lower() in ('pokemon', 'name', 'no.', '#'):
                        continue
                    notes_parts = [_clean(' '.join(c.css('::text').getall())) for c in cells[1:]]
                    notes = ' | '.join(p for p in notes_parts if p) or None
                    rank += 1
                    yield RaidCounterItem(
                        pokemon_name=pokemon_name,
                        tera_type=tera_type,
                        counter_pokemon=name_cell,
                        rank=rank,
                        notes=notes,
                    )

            elif tag in ('ul', 'ol'):
                for li in el.css('li'):
                    name = _clean(' '.join(li.css('::text').getall()))
                    if not name:
                        continue
                    rank += 1
                    yield RaidCounterItem(
                        pokemon_name=pokemon_name,
                        tera_type=tera_type,
                        counter_pokemon=name,
                        rank=rank,
                        notes=None,
                    )
