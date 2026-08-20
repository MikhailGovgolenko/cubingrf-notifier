"""Fetch and parse round results, round rosters and registrant info.

All parsing is defensive: a single malformed row is skipped rather than
failing the whole run, matching the style of ``cubingrf_html.py``.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional, Tuple

from selectolax.parser import HTMLParser, Node

from ..scrapers.http import fetch_text
from .models import RoundResult, RoundRoster

logger = logging.getLogger(__name__)


def _seconds_to_centis(text: str) -> Optional[int]:
    """Convert a displayed time like '8.86' (seconds) to centiseconds.

    Accepts an optional leading minus for DNF-style values; returns None when
    the text is not a decimal number.
    """
    m = re.match(r"\s*(-?\d+)(?:\.(\d{1,2}))?\s*$", text)
    if not m:
        return None
    whole = int(m.group(1))
    frac = (m.group(2) or "")[:2].ljust(2, "0")
    return whole * 100 + int(frac)


class CubingRFResultsScraper:
    """Scrapes per-round results and rosters from cubingrf.org.

    URLs it reads:
      * ``/competitions/{id}/competitors``  — registrant id for an RSF id.
      * ``/competitions/{id}/results/{event}/{round}`` — the actual results.
      * ``/competitions/{id}/groups/{event}/{round}``  — the round roster.
      * ``/competitions/{id}/results`` — all (event, round) pairs for the comp.
    """

    BASE_URL = "https://cubingrf.org"
    _USER_AGENT = "cubingrf-notifier/0.1"

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base = base_url.rstrip("/")

    # ------------------------------------------------------------------ http

    async def _get(self, path: str) -> Optional[str]:
        return await fetch_text(f"{self._base}{path}", user_agent=self._USER_AGENT)

    # --------------------------------------------------------- registrant map

    def _person_paths(self, tree: HTMLParser) -> dict[str, int]:
        """Map ``/persons/{RSF}`` -> per-competition registrant id.

        The competitors page renders one row per participant holding both a
        ``/persons/{CODE}`` profile link and a ``ID: {numeric}`` token.
        """
        mapping: dict[str, int] = {}
        for row in tree.css("tr"):
            link = row.css_first('a[href*="/persons/"]')
            if link is None:
                continue
            href = link.attributes.get("href", "")
            rsf = href.rstrip("/").rsplit("/", 1)[-1]
            if not rsf:
                continue
            text = row.text() or ""
            m = re.search(r"ID:\s*(\d+)", text)
            if not m:
                continue
            mapping[rsf] = int(m.group(1))
        return mapping

    async def get_registrant_id(self, competition_id: str, rsf_id: str) -> Optional[int]:
        """Numeric registrant id for an RSF id in this competition, or None."""
        html = await self._get(f"/competitions/{competition_id}/competitors")
        if html is None:
            return None
        mapping = self._person_paths(HTMLParser(html))
        return mapping.get(rsf_id)

    # ----------------------------------------------------------------- rounds

    def _round_links(self, tree: HTMLParser) -> list[Tuple[str, int]]:
        """All ``(event_code, round_number)`` pairs selectable on the comp.

        Read from the round picker that carries ``data-event`` / ``data-round``
        attributes (present on both the results and groups pages).
        """
        pairs: list[Tuple[str, int]] = []
        for el in tree.css("[data-event][data-round]"):
            event = el.attributes.get("data-event", "")
            try:
                rnd = int(el.attributes.get("data-round", ""))
            except ValueError:
                continue
            if event:
                pairs.append((event, rnd))
        return pairs

    async def get_round_pairs(self, competition_id: str) -> list[Tuple[str, int]]:
        """All (event, round) pairs for a competition, in site order."""
        html = await self._get(f"/competitions/{competition_id}/results")
        if html is None:
            return []
        return self._round_links(HTMLParser(html))

    # ------------------------------------------------------------------ results

    def _parse_results(self, html: str) -> list[RoundResult]:
        tree = HTMLParser(html)
        results: list[RoundResult] = []
        for entry in tree.css(".result-entry"):
            parsed = self._parse_result_entry(entry)
            if parsed is not None:
                results.append(parsed)
        return results

    def _parse_result_entry(self, entry: Node) -> Optional[RoundResult]:
        try:
            rid_attr = entry.attributes.get("data-registrant-id")
            if not rid_attr:
                return None
            registrant_id = int(rid_attr)

            # Place is the bold number in the leading w-fit cell.
            place = None
            place_el = entry.css_first("div.w-fit")
            if place_el is not None:
                pm = re.search(r"\d+", place_el.text() or "")
                if pm:
                    place = int(pm.group())

            # Per-attempt times: elements carrying data-raw-result.
            attempts: list[int] = []
            for cell in entry.css("[data-raw-result]"):
                raw = cell.attributes.get("data-raw-result", "").strip()
                if not raw:
                    continue
                try:
                    attempts.append(int(raw))
                except ValueError:
                    continue

            # Best is the fastest non-DNF attempt (centiseconds).
            valid = [a for a in attempts if a >= 0]
            best = min(valid) if valid else None

            # Average text is in "seconds" form ("8.86"); convert to centiseconds.
            average = None
            avg_el = entry.css_first("span.font-bold")
            if avg_el is not None:
                average = _seconds_to_centis(avg_el.text() or "")

            # Advanced-to-next-round marker.
            advanced = "bg-green-300" in (entry.attributes.get("class", "") or "")

            return RoundResult(
                registrant_id=registrant_id,
                place=place or 0,
                attempts=tuple(attempts),
                average=average,
                best=best,
                advanced=advanced,
            )
        except Exception:
            logger.exception("Failed to parse a result entry; skipping")
            return None

    async def fetch_round_results(
        self,
        competition_id: str,
        event: str,
        round_number: int,
    ) -> list[RoundResult]:
        html = await self._get(
            f"/competitions/{competition_id}/results/{event}/{round_number}"
        )
        if html is None:
            return []
        return self._parse_results(html)

    # ------------------------------------------------------------------- roster

    def _parse_roster(self, html: str) -> RoundRoster:
        tree = HTMLParser(html)
        # The groups page lists every participant as a row that links to their
        # profile via /persons/{RSF}. The roster count is all this page gives
        # us unambiguously; it is what the completion heuristic needs.
        count = 0
        for row in tree.css("tr"):
            if row.css_first('a[href*="/persons/"]') is not None:
                count += 1
        return RoundRoster(count=count)

    async def fetch_round_roster(
        self,
        competition_id: str,
        event: str,
        round_number: int,
    ) -> RoundRoster:
        html = await self._get(
            f"/competitions/{competition_id}/groups/{event}/{round_number}"
        )
        if html is None:
            return RoundRoster()
        return self._parse_roster(html)

    # ------------------------------------------------------------- convenience

    async def fetch_many_results(
        self,
        competition_id: str,
        pairs: list[Tuple[str, int]],
    ) -> dict[Tuple[str, int], list[RoundResult]]:
        """Fetch several rounds concurrently into a {pair: results} dict.

        Rounds that fail to load are omitted rather than raising.
        """
        if not pairs:
            return {}
        results = await asyncio.gather(
            *(
                self.fetch_round_results(competition_id, event, rnd)
                for event, rnd in pairs
            )
        )
        return dict(zip(pairs, results))
