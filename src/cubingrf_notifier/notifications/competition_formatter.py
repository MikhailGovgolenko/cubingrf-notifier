"""Single source of truth for competition text formatting.

Used both by the bot's "competitions" page and by push notifications, so the
output is always identical and localized the same way.
"""
from datetime import datetime
from typing import List, Optional

from ..competitions.disciplines import discipline_short_label, sort_discipline_codes
from ..i18n import get_text

# Separator between competition cards, spanning the full message width.
CARD_SEPARATOR = "─" * 18

_RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

_EN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

_REG_LABEL_KEYS = {
    "open": "competitions.reg_open",
    "scheduled": "competitions.reg_scheduled",
    "closed": "competitions.reg_closed",
}


def format_date(d: datetime | None, language: str = "ru") -> str:
    if d is None:
        return get_text(language, "unknown_date")
    months = _RU_MONTHS if language == "ru" else _EN_MONTHS
    return f"{d.day} {months[d.month]} {d.year}"


def format_date_range(
    start: datetime | None,
    end: datetime | None,
    language: str = "ru",
) -> str:
    """Localized date label: single day or a multi-day range.

    Single day:        "7 августа 2026"
    Same month range:  "4–6 декабря 2026"
    Cross month/year:  "28 декабря 2026 — 3 января 2027"
    """
    if start is None:
        return get_text(language, "unknown_date")
    if end is None or end <= start:
        return format_date(start, language)
    if start.month == end.month and start.year == end.year:
        months = _RU_MONTHS if language == "ru" else _EN_MONTHS
        return f"{start.day}–{end.day} {months[start.month]} {start.year}"
    return f"{format_date(start, language)} — {format_date(end, language)}"


def short_location(location: str | None) -> str:
    """Trim "Region, City" to just the city for a compact card."""
    if not location:
        return "-"
    city = location.split(",", 1)[-1].strip()
    return city or location


def disciplines_line(codes: List[str], language: str) -> str | None:
    """Full discipline line: "3x3 • 4x4 • OH", nothing truncated."""
    if not codes:
        return None
    labels = [discipline_short_label(c) for c in sort_discipline_codes(codes)]
    return f"{get_text(language, 'competitions.disciplines')} {' • '.join(labels)}"


def format_competition_card(competition, language: str = "ru") -> str:
    """A competition card without any page header.

    Used on the competitions page (joined with CARD_SEPARATOR) and as the body
    of a notification.
    """
    lines = [
        f"🏆 {competition.name}",
        "",
        get_text(language, "competitions.date", date=format_date_range(
            competition.date, getattr(competition, "end_date", None), language,
        )),
        get_text(language, "competitions.location", location=short_location(competition.location)),
    ]

    disc_line = disciplines_line(competition.disciplines or [], language)
    if disc_line:
        lines.append("")
        lines.append(disc_line)

    reg_key = _REG_LABEL_KEYS.get(competition.reg_status or "")
    if reg_key:
        lines.append("")
        lines.append(get_text(language, reg_key))

    if competition.url:
        lines.append("")
        lines.append(f"🔗 {competition.url}")

    return "\n".join(lines)


def format_competition_notification(competition, language: str = "ru") -> str:
    """Full push-notification text: localized header + the standard card."""
    header = get_text(language, "notifications.title")
    return f"{header}\n\n{format_competition_card(competition, language)}"