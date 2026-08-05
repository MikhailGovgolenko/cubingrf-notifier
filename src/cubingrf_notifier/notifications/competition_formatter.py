"""Single source of truth for competition text formatting.

Used both by the bot's "competitions" page and by push notifications, so the
output is always identical and localized the same way.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import re

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

# Characters that start/end formatting in Telegram legacy Markdown and must be
# escaped inside a link label.
_TG_MD_ESCAPE_RE = re.compile(r"([\\_*\[\]()`])")


def _tg_escape(text: str) -> str:
    """Escape Telegram legacy-Markdown specials so raw text is shown verbatim."""
    return _TG_MD_ESCAPE_RE.sub(r"\\\1", text)


def _title_line(competition) -> str:
    """Competition name; a Telegram Markdown link to the page when available."""
    name = competition.name or ""
    if not competition.url:
        return f"🏆 {name}"
    return f"🏆 [{_tg_escape(name)}]({competition.url})"


def _ru_plural(count: int, forms: tuple[str, str, str]) -> str:
    """Russian plural: forms = (one, few, many)."""
    n = abs(count) % 100
    if 10 < n < 20:
        return forms[2]
    n %= 10
    if n == 1:
        return forms[0]
    if 2 <= n <= 4:
        return forms[1]
    return forms[2]


_RU_UNITS = {
    "day": ("день", "дня", "дней"),
    "hour": ("час", "часа", "часов"),
    "minute": ("минуту", "минуты", "минут"),
}
_EN_UNITS = {"day": "day", "hour": "hour", "minute": "minute"}


def format_registration_countdown(
    registration_start_at: datetime | None,
    language: str = "ru",
    now: datetime | None = None,
) -> str | None:
    """Localized "registration opens in N days/hours/minutes".

    Returns None (caller keeps the previous label) when there is no opening
    time, when it already passed, or when the remaining time is zero — so no
    wrong/negative values are ever emitted.
    """
    if registration_start_at is None:
        return None
    if now is None:
        now = datetime.now(timezone.utc)
    start = registration_start_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    remaining = start.astimezone(timezone.utc) - now.astimezone(timezone.utc)
    if remaining <= timedelta(0):
        return None

    total_minutes = max(1, int(remaining.total_seconds() // 60))
    if total_minutes < 60:
        count, key = total_minutes, "minute"
    elif total_minutes < 24 * 60:
        count, key = total_minutes // 60, "hour"
    else:
        count, key = total_minutes // (24 * 60), "day"

    if language == "ru":
        unit = _ru_plural(count, _RU_UNITS[key])
    else:
        unit = _EN_UNITS[key] + ("" if count == 1 else "s")

    return get_text(language, "competitions.reg_opening_in", count=count, unit=unit)


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
        _title_line(competition),
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
        label = get_text(language, reg_key)
        if reg_key == "competitions.reg_scheduled":
            countdown = format_registration_countdown(
                getattr(competition, "registration_start_at", None),
                language,
            )
            if countdown is not None:
                label = countdown
        lines.append("")
        lines.append(label)

    return "\n".join(lines)


def format_competition_notification(competition, language: str = "ru") -> str:
    """Full push-notification text: localized header + the standard card."""
    header = get_text(language, "notifications.title")
    return f"{header}\n\n{format_competition_card(competition, language)}"


def format_registration_reminder(competition, language: str = "ru") -> str:
    """Text for the "registration opens in 30 minutes" reminder."""
    header = get_text(language, "notifications.reg_soon")
    return f"{header}\n\n{format_competition_card(competition, language)}"