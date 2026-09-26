"""Localized Rich Message formatting for round result notifications."""
from __future__ import annotations

from html import escape

from ..i18n import get_text
from ..competitions.disciplines import discipline_label
from .models import RoundSnapshot

# Events whose results are move counts instead of times. Fewest Moves stores
# each attempt as the raw move count; its "average" is a fixed-point mean with
# two decimals (37+38+41 -> "38.67"), scaled like centiseconds.
_MOVE_COUNT_EVENTS = {"333fm"}


def _is_move_count_event(event_code: str | None) -> bool:
    return event_code in _MOVE_COUNT_EVENTS


def _format_move(value: int) -> str:
    """A single FMC value (move count): 37 -> '37', -1 -> 'DNF', -2 -> 'DNS'."""
    if value == -1:
        return "DNF"
    if value == -2:
        return "DNS"
    return str(value)


def _format_move_fixed(value: int) -> str:
    """FMC fixed-point value (2 dp): 3867 -> '38.67'; -1 -> 'DNF'."""
    if value == -1:
        return "DNF"
    if value == -2:
        return "DNS"
    return f"{value / 100:.2f}"


def format_time(centis: int | None, language: str = "ru") -> str:
    """Centiseconds -> '13.45'; 'M:SS.CC' once at least a minute long.

    Under a minute a time renders as ``SS.CC`` (e.g. '36.07'). From one
    minute up, in the speedcubing convention: ``M:SS.CC`` with zero-padded
    seconds (e.g. '1:46.13', '1:06.13'). From one hour up, ``H:MM:SS.CC``.
    DNF (-1) -> 'DNF'. DNS (-2) -> 'DNS'. None -> '-'."""
    if centis is None:
        return "-"
    if centis == -1:
        return "DNF"
    if centis == -2:
        return "DNS"
    total_seconds, remaining = divmod(centis, 100)
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{remaining:02d}"
    if total_seconds >= 60:
        return f"{minutes}:{seconds:02d}.{remaining:02d}"
    return f"{seconds}.{remaining:02d}"


def format_attempts(
    snapshot: RoundSnapshot, language: str = "ru", event_code: str | None = None
) -> str | None:
    """Attempts joined with commas, e.g. '9.12, 8.88, 8.45, 9.30, 8.55'."""
    if not snapshot.attempts:
        return None
    if _is_move_count_event(event_code):
        return ", ".join(_format_move(t) for t in snapshot.attempts)
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

    Rendered as a Telegram Rich Message: ``<h1>`` heading, links with
    ``<a href>`` and ``<br/>`` line breaks. The layout uses blank lines
    between top-level blocks and single line breaks within a block.
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

    # Blocks, ordered top to bottom, separated from each other by a blank line.
    blocks: list[str] = [
        f"<h1>{heading}</h1>",
        comp_link,
        title,
    ]

    if snapshot.place:
        blocks.append(get_text(language, "results.place", place=snapshot.place))

    # Attempts and the average/best share one block (single <br/> between).
    detail_lines: list[str] = []
    attempts = format_attempts(snapshot, language, event_code=event_code)
    if attempts:
        detail_lines.append(get_text(language, "results.attempts", attempts=attempts))
    moves = _is_move_count_event(event_code)
    info: list[str] = []
    if snapshot.average is not None:
        avg_text = (
            _format_move_fixed(snapshot.average) if moves else format_time(snapshot.average, language)
        )
        info.append(get_text(language, "results.average", time=avg_text))
    if snapshot.best is not None:
        best_text = (
            _format_move(snapshot.best) if moves else format_time(snapshot.best, language)
        )
        info.append(get_text(language, "results.best", time=best_text))
    if info:
        detail_lines.append(" • ".join(info))
    if detail_lines:
        blocks.append("<br/>".join(detail_lines))

    if snapshot.advanced:
        blocks.append(get_text(language, "results.advanced"))

    # The <h1> heading carries its own visual line, so the competition name
    # sits directly beneath it (no <br/> between them). Every later block is
    # separated by a single blank line (<br/><br/>).
    return f"{blocks[0]}{blocks[1]}" + ("<br/><br/>" + "<br/><br/>".join(blocks[2:]) if len(blocks) > 2 else "")