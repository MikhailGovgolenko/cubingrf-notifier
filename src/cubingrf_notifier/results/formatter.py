"""Localized Rich Message formatting for round result notifications."""
from __future__ import annotations

from html import escape

from ..i18n import get_text
from ..competitions.disciplines import discipline_label
from .models import RoundSnapshot


def format_time(centis: int | None, language: str = "ru") -> str:
    """Centiseconds -> '13.45'. DNF (-1) -> 'DNF'. None -> '-'."""
    if centis is None:
        return "-"
    if centis < 0:
        return "DNF"
    seconds, remaining = divmod(centis, 100)
    return f"{seconds}.{remaining:02d}"


def format_attempts(snapshot: RoundSnapshot, language: str = "ru") -> str | None:
    """Attempts joined with commas, e.g. '9.12, 8.88, 8.45, 9.30, 8.55'."""
    if not snapshot.attempts:
        return None
    return ", ".join(format_time(t, language) for t in snapshot.attempts)


def format_round_result(
    competition_name: str,
    competition_url: str | None,
    event_code: str,
    round_number: int,
    snapshot: RoundSnapshot,
    language: str = "ru",
    edited: bool = False,
) -> str:
    """A full notification for a finished (or edited) round.

    Rendered as a Telegram Rich Message: ``<h1>`` heading, bold title, links
    with ``<a href>`` and ``<br/>`` line breaks.
    """
    if edited:
        heading = get_text(language, "results.notification_edited")
    else:
        heading = get_text(language, "results.notification_new")

    name = escape(competition_name or "")
    if competition_url:
        comp_link = f'<a href="{escape(competition_url)}">{name}</a>'
    else:
        comp_link = name

    title = get_text(
        language,
        "results.title",
        event=discipline_label(event_code),
        round=round_number,
    )

    lines = [
        f"🏆 <b>{comp_link}</b>",
    ]

    if snapshot.place:
        lines.append(get_text(language, "results.place", place=snapshot.place))

    attempts = format_attempts(snapshot, language)
    if attempts:
        lines.append(get_text(language, "results.attempts", attempts=attempts))

    info: list[str] = []
    if snapshot.average is not None:
        info.append(get_text(language, "results.average", time=format_time(snapshot.average, language)))
    if snapshot.best is not None:
        info.append(get_text(language, "results.best", time=format_time(snapshot.best, language)))
    if snapshot.advanced:
        info.append(get_text(language, "results.advanced"))
    if info:
        lines.append(" • ".join(info))

    body = "<br/>".join(lines)
    return f"<h1>{heading}</h1>\n<p>{title}</p>\n<br/>{body}"