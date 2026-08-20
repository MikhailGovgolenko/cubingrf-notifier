from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

import asyncio
import logging
import re

from selectolax.parser import HTMLParser

from ..competitions.models import CompetitionDTO
from .base import CompetitionSource
from .http import fetch_text

logger = logging.getLogger(__name__)


# Russian month names used on cubingrf.org ("22 августа 2026", "7 - 9 августа 2026")
RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

# Locate "<day> ... <month> <year>" inside a human-readable date string.
_DATE_RE = re.compile(r"(\d{1,2})[^а-яё]*?([а-яё]+)[^\d]*?(\d{4})", re.IGNORECASE)

# Same-month range: "7 - 9 августа 2026".
_RANGE_DAY_RE = re.compile(
    r"(\d{1,2})\s*(?:[–—-]|до)\s*(\d{1,2})\s+([а-яё]+)\s+(\d{4})",
    re.IGNORECASE,
)

# Cross-month/year range: "28 декабря 2026 - 3 января 2027".
_RANGE_FULL_RE = re.compile(
    r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s*(?:[–—-]|до)\s*(\d{1,2})\s+([а-яё]+)\s+(\d{4})",
    re.IGNORECASE,
)

# Registration availability detected in a competition card's status text.
_OPEN = "open"
_SCHEDULED = "scheduled"
_CLOSED = "closed"
_CANCELLED = "cancelled"

# Moscow time is UTC+3 all year; the site states offsets explicitly ('МСК+0',
# 'МСК+4', ...) next to the registration window.
MSK_UTC_OFFSET = 3

# "Регистрация участников с 16 августа 2026 10:00 по ... (часовой пояс: МСК+0, ...)".
_REG_START_RE = re.compile(
    r"Регистрация участников с\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?",
    re.IGNORECASE,
)
_MSK_OFFSET_RE = re.compile(r"МСК([+-]\d{1,2})", re.IGNORECASE)


def parse_registration_start(text: str) -> Optional[datetime]:
    """Parse the registration opening moment into a tz-aware UTC datetime.

    Handles 'Регистрация участников с 16 августа 2026 10:00 по ...' where the
    clock time may be absent and the time zone is given as 'МСК+N'. Returns
    None when there is no match or when no clock time is provided (a bare date
    cannot schedule a 30-minute reminder), never raises.
    """
    if not text:
        return None
    match = _REG_START_RE.search(text)
    if not match:
        return None
    month = RU_MONTHS.get(match.group(2).lower())
    if not month:
        return None
    if not match.group(4):
        return None
    try:
        offset = MSK_UTC_OFFSET
        tz_match = _MSK_OFFSET_RE.search(text)
        if tz_match:
            offset += int(tz_match.group(1))
        local = datetime(
            int(match.group(3)),
            month,
            int(match.group(1)),
            int(match.group(4)),
            int(match.group(5)),
            tzinfo=timezone(timedelta(hours=offset)),
        )
    except ValueError:
        return None
    return local.astimezone(timezone.utc)


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
    return _build_date(int(match.group(1)), RU_MONTHS.get(match.group(2).lower()), int(match.group(3)))


def _build_date(day: int, month: Optional[int], year: int) -> Optional[datetime]:
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def parse_russian_date_range(text: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse a Russian date range into (start, end) datetimes.

    Handles single dates ('22 августа 2026' -> end=None), same-month ranges
    ('7 - 9 августа 2026') and cross-month/year ranges ('28 декабря 2026 -
    3 января 2027'). Returns (None, None) when parsing fails (never raises).
    """
    start = parse_russian_date(text)
    if start is None:
        return None, None

    m = _RANGE_FULL_RE.search(text)
    if m:
        end = _build_date(int(m.group(4)), RU_MONTHS.get(m.group(5).lower()), int(m.group(6)))
        if end is not None:
            return start, end

    m = _RANGE_DAY_RE.search(text)
    if m:
        end = _build_date(int(m.group(2)), start.month, start.year)
        if end is not None:
            return start, end

    return start, None


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

        await self._enrich_details(items)

        logger.info("Parsed %d competitions from %s", len(items), self._competitions_url)
        return items

    async def _enrich_details(self, items: List[CompetitionDTO]) -> None:
        """Fill registration_start_at and name_en from detail pages.

        Each competition's detail page is fetched exactly once and yields both
        the registration-window text and the English competition name.
        Registration start is parsed only for competitions whose registration
        has not opened yet; the English name is read for every competition
        that lacks one. A failed page fetch is skipped silently so parsing
        never breaks.
        """
        pending = [
            item
            for item in items
            if item.reg_status in (None, _SCHEDULED) or not item.name_en
        ]
        if not pending:
            return
        details = await asyncio.gather(*(self._fetch_details(item.url) for item in pending))
        for item, (reg_text, name_en) in zip(pending, details):
            if item.reg_status in (None, _SCHEDULED):
                item.registration_start_at = parse_registration_start(reg_text)
            if name_en:
                item.name_en = name_en

    async def _fetch_details(self, url: str) -> tuple[str, Optional[str]]:
        """Return (registration-window text, English name) from a detail page.

        The English name sits in the first bare ``<div>`` of the page's second
        "text-lg font-bold mb-4" block: the first such block holds the Russian
        ``<h2>`` title plus status, the second holds the English title, the
        dates and the city. Returns ('', None) on any error.
        """
        html = await self._get_page(url)
        if html is None:
            return "", None
        tree = HTMLParser(html)

        reg_text = ""
        for el in tree.css("div"):
            text = (el.text() or "").strip()
            if text.startswith("Регистрация участников с") or text.startswith("Регистрация с"):
                reg_text = text
                break

        return reg_text, self._extract_english_name(tree)

    @staticmethod
    def _extract_english_name(tree: HTMLParser) -> Optional[str]:
        """Read the English competition name from a detail page, or None."""
        try:
            for block in tree.css("div.text-lg.font-bold.mb-4"):
                if block.css_first("h2") is not None:
                    continue  # Russian title block (h2 + status), not the English one
                for child in block.iter():
                    if child.tag == "div":
                        name = (child.text() or "").strip()
                        return name or None
        except Exception:
            logger.exception("Failed to extract English name; skipping")
        return None

    async def _get_page(self, url: str) -> Optional[str]:
        """Fetch page HTML; return None on any error instead of raising."""
        return await fetch_text(url)

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
            reg_status = self._extract_reg_status(card)

            start_date, end_date = None, None
            if date_el is not None:
                start_date, end_date = parse_russian_date_range(date_el.text())

            return CompetitionDTO(
                external_id=external_id,
                name=name_el.text().strip() if name_el is not None else external_id,
                location=location,
                date=start_date,
                end_date=end_date,
                url=link,
                disciplines=disciplines,
                reg_status=reg_status,
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

    def _extract_reg_status(self, card) -> Optional[str]:
        """Normalize the registration status shown on a competition card.

        Returns 'open', 'scheduled', 'closed', 'cancelled' or None when the
        status text cannot be interpreted (never raises).
        """
        try:
            status_el = card.css_first(".status")
            if status_el is None:
                return None
            text = status_el.text().lower()
            return self._normalize_reg_status(text)
        except Exception:
            return None

    @staticmethod
    def _normalize_reg_status(text: str) -> Optional[str]:
        text = text.lower()
        # Cancellation is checked first: a cancelled competition must never be
        # shown with a misleading "registration open/closed" label, even if the
        # card text also contains one of the registration phrases.
        if "отмен" in text:
            return _CANCELLED
        if (
            "регистрация закрыта" in text
            or "результаты утверждены" in text
            or "завершено" in text
        ):
            return _CLOSED
        if "идёт регистрация" in text:
            return _OPEN
        if "до регистрации" in text:
            return _SCHEDULED
        return None
