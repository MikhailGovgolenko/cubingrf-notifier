from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import httpx
import logging
import re

from selectolax.parser import HTMLParser

from ..competitions.models import CompetitionDTO
from .base import CompetitionSource

logger = logging.getLogger(__name__)


# Russian month names used on cubingrf.org ("22 августа 2026", "7 - 9 августа 2026")
RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

# Locate "<day> ... <month> <year>" inside a human-readable date string.
_DATE_RE = re.compile(r"(\d{1,2})[^а-яё]*?([а-яё]+)[^\d]*?(\d{4})", re.IGNORECASE)


def parse_russian_date(text: str) -> Optional[datetime]:
    """Parse a Russian date like '22 августа 2026' into a datetime.

    For date ranges ('7 - 9 августа 2026') the start day is used.
    Returns None when the string cannot be parsed (never raises).
    """
    if not text:
        return None
    match = _DATE_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    month = RU_MONTHS.get(match.group(2).lower())
    year = int(match.group(3))
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def extract_external_id(url: str) -> Optional[str]:
    """Return the last path segment of a competition URL, e.g. 'SPBCotD2026'."""
    path = urlparse(url).path.rstrip("/")
    if not path:
        return None
    return path.rsplit("/", 1)[-1]


class CubingRFHtmlScraper(CompetitionSource):
    """Scrapes cubingrf.org competitions page using HTML parsing.

    Reads competition cards from the currently active (current year) tab.
    Parsing is defensive: a single malformed card is skipped instead of
    failing the whole run.
    """

    BASE_URL = "https://cubingrf.org/"
    COMPETITIONS_PATH = "competitions"
    # Competition cards are <a class="block p-5 border ... rounded h-full">
    _CARD_SELECTOR = "a.block.p-5"

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._competitions_url = base_url.rstrip("/") + "/" + self.COMPETITIONS_PATH

    async def fetch_competitions(self) -> List[CompetitionDTO]:
        html = await self._get_page(self._competitions_url)
        if html is None:
            return []

        tree = HTMLParser(html)
        cards = self._select_cards(tree)
        if not cards:
            logger.warning("No competition cards found on %s; site markup may have changed", self._competitions_url)
            return []

        items: List[CompetitionDTO] = []
        seen: set[str] = set()
        for card in cards:
            dto = self._parse_card(card)
            if dto is None or dto.external_id in seen:
                continue
            seen.add(dto.external_id)
            items.append(dto)

        logger.info("Parsed %d competitions from %s", len(items), self._competitions_url)
        return items

    async def _get_page(self, url: str) -> Optional[str]:
        """Fetch page HTML; return None on any error instead of raising."""
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "cubingrf-notifier/0.1"})
                r.raise_for_status()
                return r.text
        except httpx.HTTPError as exc:
            logger.exception("Failed to fetch %s: %s", url, exc)
            return None

    def _select_cards(self, tree: HTMLParser) -> List:
        """Pick competition cards from the active (current year) tab.

        Falls back to any matching card in the document if no active tab
        is present, so the scraper keeps working if tabs change.
        """
        active_tab = tree.css_first('[data-te-tab-active]')
        if active_tab is not None:
            cards = active_tab.css(self._CARD_SELECTOR)
            if cards:
                return cards
        return tree.css(self._CARD_SELECTOR)

    def _parse_card(self, card) -> Optional[CompetitionDTO]:
        try:
            link = card.attributes.get("href")
            if not link:
                return None
            external_id = extract_external_id(link)
            if not external_id:
                return None

            name_el = card.css_first("div.font-bold.text-lg")
            date_el = card.css_first("div.text-gray-500.text-sm")

            # Location lives in the first "div.text-base"; the region is in an <img title="...">.
            location = self._extract_location(card)
            disciplines = self._extract_disciplines(card)

            return CompetitionDTO(
                external_id=external_id,
                name=name_el.text().strip() if name_el is not None else external_id,
                location=location,
                date=parse_russian_date(date_el.text()) if date_el is not None else None,
                url=link,
                disciplines=disciplines,
            )
        except Exception:
            logger.exception("Failed to parse competition card; skipping")
            return None

    def _extract_location(self, card) -> Optional[str]:
        """Combine region name (from <img title>) and city name."""
        try:
            loc_div = card.css_first("div.text-base")
            if loc_div is None:
                return None
            city = loc_div.text().strip()
            region_el = loc_div.css_first("img[title]")
            if region_el is not None:
                region = region_el.attributes.get("title", "").strip()
                if region:
                    return f"{region}, {city}".strip(", ") if city else region
            return city or None
        except Exception:
            return None

    def _extract_disciplines(self, card) -> List[str]:
        """Extract event codes from '<i class="cubing-icon event-XXX">'."""
        try:
            codes = []
            for icon in card.css("i.cubing-icon"):
                for cls in (icon.attributes.get("class") or "").split():
                    if cls.startswith("event-"):
                        codes.append(cls.removeprefix("event-"))
            return codes
        except Exception:
            return []
