"""Data models for round results scraped from cubingrf.org.

All values are parsed from the round results page
(``/competitions/{id}/results/{event}/{round}``) and the round roster page
(``/competitions/{id}/groups/{event}/{round}``).

Centiseconds are the raw unit the site uses for times (``data-raw-result``);
a value of ``-1`` means a DNF attempt. Solves are rendered for humans by the
formatter, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoundResult:
    """A single participant's result in one round."""

    registrant_id: int
    place: int
    # Five per-attempt times in centiseconds (-1 == DNF); shorter for
    # multi-blind/fewest-moves style events where fewer solves are counted.
    attempts: tuple[int, ...] = field(default_factory=tuple)
    # Averages/best in centiseconds (or None when the value is not shown).
    average: int | None = None
    best: int | None = None
    # True when the round advanced this participant (bg-green-300 marker).
    advanced: bool = False


@dataclass(frozen=True)
class RoundSnapshot:
    """The user's own result within a round (what gets persisted/notified)."""

    place: int | None = None
    attempts: tuple[int, ...] = ()
    average: int | None = None
    best: int | None = None
    advanced: bool = False


@dataclass(frozen=True)
class RoundRoster:
    """The participants list of a round (for the "everyone finished?" check)."""

    registrant_ids: tuple[int, ...] = ()
    count: int = 0
