"""Single source of truth for competition text formatting (Rich Message HTML).

Used both by the bot's "competitions" page and by push notifications, so the
output is always identical and localized the same way. Everything is rendered
as a Telegram Rich Message (``sendRichMessage``): headings use ``<h1>``, links
use ``<a href>``, cards are ``<p>`` blocks, line breaks use ``<br/>`` and
sections are split by ``<hr/>``.

Note: a literal ``\\n`` collapses in Rich Message HTML, so every line break
between fields is rendered with ``<br/>``.
"""
from datetime import datetime, timedelta, timezone
from typing import List
from html import escape

from ..competitions.disciplines import discipline_short_label, sort_discipline_codes
from ..competitions.localization import localize_city
from ..i18n import get_text

# Separator block between cards (rendered as a rich-message <hr/>).
CARD_SEPARATOR = "<hr/>"

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
    "cancelled": "competitions.reg_cancelled",
}


def _escape(text: str) -> str:
    """Escape HTML specials so untrusted text renders verbatim."""
    return escape(text, quote=True)


def _heading(text: str) -> str:
    """A page/notification heading (Rich Message ``<h1>``)."""
    return f"<h1>{_escape(text)}</h1>"


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

    # Round down (floor) to whole units in every band so the bot matches the
    # source site, which never inflates a wait: 15h25m reads "15 часов", a
    # 2.x-day wait reads "2 дня". Each band is floored independently so the
    # unit chosen for a given duration is the site's too (a 23h59m wait shows
    # "23 часа", not "1 день"). The minimum of 1 keeps an almost-open
    # registration from reading "0".
    total_minutes = remaining.total_seconds() / 60
    if total_minutes < 60:
        count, key = max(1, int(total_minutes)), "minute"
    elif total_minutes < 24 * 60:
        count, key = max(1, int(total_minutes / 60)), "hour"
    else:
        count, key = max(1, int(total_minutes / (24 * 60))), "day"

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


def short_location(location: str | None, language: str = "ru") -> str:
    """Trim "Region, City" to just the city for a compact card.

    For English the city is localized (the site only provides Russian city
    names); Russian and unknown languages keep the original city.
    """
    if not location:
        return "-"
    city = location.split(",", 1)[-1].strip() or location
    return localize_city(city, language)


def disciplines_line(codes: List[str], language: str) -> str | None:
    """Full discipline line: "3x3 • 4x4 • OH", nothing truncated."""
    if not codes:
        return None
    labels = [discipline_short_label(c) for c in sort_discipline_codes(codes)]
    return f"{get_text(language, 'competitions.disciplines')} {' • '.join(labels)}"


def _title_line(competition, language: str) -> str:
    """Bold title; an HTML link to the page when a URL is available.

    English users see the site's English name when it provides one; otherwise
    the Russian name is the fallback.
    """
    name = competition.name or ""
    if language == "en":
        name = getattr(competition, "name_en", None) or name
    name = _escape(name)
    if not getattr(competition, "url", None):
        return f"🏆 <b>{name}</b>"
    return f'🏆 <b><a href="{_escape(competition.url)}">{name}</a></b>'


def _registration_label(competition, language: str, countdown_at=None) -> str | None:
    reg_key = _REG_LABEL_KEYS.get(competition.reg_status or "")
    if not reg_key:
        return None
    label = get_text(language, reg_key)
    if reg_key == "competitions.reg_scheduled":
        countdown = format_registration_countdown(
            getattr(competition, "registration_start_at", None),
            language,
            now=countdown_at,
        )
        if countdown is not None:
            label = countdown
    return label


def format_competition_card(competition, language: str = "ru", countdown_at=None) -> str:
    """A competition card without any page header.

    Used on the competitions page (as a ``<p>`` block) and as the body of a
    notification. The card opens with a single line break before the title and closes with a
    blank line; groups of fields are separated by blank lines
    (``<br/><br/>``)::

        <br/>🏆 <b><a href="...">Name</a></b>

        📅 22 August 2026<br/>
        📍 Мисайлово

        🧩 4x4 • 5x5

        🟢 Registration is open
        <br/><br/>

    ``countdown_at`` is the instant the countdown is measured from. When
    omitted (None) the real current time is used — this is the behaviour of
    the /competitions page and stays untouched. Registration reminders pass
    their *scheduled* delivery instant here so a few seconds of scheduler
    delay never shave a minute off the displayed value.
    """
    title = _title_line(competition, language)
    date = get_text(
        language,
        "competitions.date",
        date=format_date_range(
            competition.date,
            getattr(competition, "end_date", None),
            language,
        ),
    )
    location = get_text(
        language,
        "competitions.location",
        location=short_location(competition.location, language),
    )

    groups = [
        [title],
        [date, location],
    ]

    disc_line = disciplines_line(competition.disciplines or [], language)
    if disc_line:
        groups.append([disc_line])

    reg_label = _registration_label(competition, language, countdown_at)
    if reg_label is not None:
        groups.append([reg_label])

    parts = groups + [[]]
    return "<br/>" + "<br/><br/>".join("<br/>".join(group) for group in parts)


def format_competition_count(total: int, language: str = "ru") -> str:
    """"📊 Found N competitions with open or upcoming registration" (localized)."""
    if language == "ru":
        unit = _ru_plural(
            total,
            ("соревнование", "соревнования", "соревнований"),
        ) + " с открытой или предстоящей регистрацией"
    else:
        base = "competition" if total == 1 else "competitions"
        unit = f"{base} with open or upcoming registration"
    return get_text(language, "competitions.count", count=total, unit=unit)


def format_competitions_page(
    competitions,
    language: str = "ru",
    total_count: int | None = None,
) -> str:
    """The full "competitions" page header + cards.

    Layout (no separator right under the heading)::

        <h1>Upcoming competitions</h1>
        <p>📊 Found 4 competitions</p>
        <hr/>
        <p>🏆 <b><a href="...">Name</a></b><br/>📅 …<br/>📍 …</p>
        <hr/>
        <p>🏆 <b><a href="...">Name</a></b><br/>📅 …<br/>📍 …</p>
        ...
    """
    header = _heading(get_text(language, "competitions.title"))
    if not competitions:
        return f"{header}\n{get_text(language, 'competitions.none')}"

    count_line = format_competition_count(total_count or len(competitions), language)
    cards = f"\n{CARD_SEPARATOR}\n".join(
        f"<p>{format_competition_card(c, language)}</p>" for c in competitions
    )
    return f"{header}\n<p>{count_line}</p>\n{CARD_SEPARATOR}\n{cards}"


def format_competition_notification(competition, language: str = "ru") -> str:
    """Full push-notification text: localized header + the standard card."""
    header = _heading(get_text(language, "notifications.title"))
    return f"{header}\n<p>{format_competition_card(competition, language)}</p>"


def format_registration_reminder(competition, language: str = "ru", countdown_at=None) -> str:
    """Text for the "registration opens soon" reminder.

    ``countdown_at`` (optional) is the scheduled delivery instant the countdown
    should be measured from; when omitted the real current time is used. The
    reminder sender passes the exact ``registration_start_at - interval``
    instant so the message shows the full interval even when the scheduler
    fires a few seconds late.
    """
    header = _heading(get_text(language, "notifications.reg_soon"))
    return f"{header}\n<p>{format_competition_card(competition, language, countdown_at=countdown_at)}</p>"
