"""Shared text helpers for bot screens (status, pickers, competition cards).

All pickers render as Telegram Rich Messages, where a literal ``\\n`` collapses
and line breaks are produced with ``<br/>``.
"""

from typing import Iterable

BULLET = "•"


def bullet_lines(items: Iterable[str]) -> str:
    """Render items one per pushed line, each prefixed with a bullet."""
    return "<br/>".join(f"{BULLET} {item}" for item in items)


def status_section(label: str, items: Iterable[str], all_text: str) -> str:
    """Status block for a multi-valued preference.

    With no items returns ``"{label} {all_text}"`` on one line; otherwise the
    label is followed by a bulleted list of the items.
    """
    items = list(items)
    if not items:
        return f"{label} {all_text}"
    return f"{label}<br/>{bullet_lines(items)}"


def selection_screen_text(title: str, none_text: str, items: Iterable[str]) -> str:
    """Picker screen: an ``<h1>`` page title, then bulleted items or a hint."""
    items = list(items)
    if not items:
        return f"<h1>{title}</h1><br/><br/>{none_text}"
    return f"<h1>{title}</h1><br/><br/>{bullet_lines(items)}"
