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
    """Convert a displayed time to centiseconds.

    Accepts ``SS.CC`` (e.g. '8.86'), ``M:SS.CC`` (e.g. '1:38.25') and
    ``H:MM:SS.CC`` spellings, plus the DNF/DNS tokens the site uses in
    result cells. DNF/DNS map to -1/-2, matching the raw result
    conventions. Returns None when the text is none of those.
    """
    token = (text or "").strip()
    if not token:
        return None
    upper = token.upper()
    if upper == "DNF":
        return -1
    if upper == "DNS":
        return -2
    whole, dot, frac = token.partition(".")
    total_parts = [p for p in whole.split(":") if p]
    if dot:
        if not frac or not frac.isdigit() or len(frac) > 2:
            return None
    else:
        frac = "00"
    if not total_parts or any(not p.isdigit() for p in total_parts):
        return None
    nums = [int(p) for p in total_parts]
    if len(nums) == 1:
        total_seconds = nums[0]
    elif len(nums) == 2:
        if nums[1] >= 60:
            return None
        total_seconds = nums[0] * 60 + nums[1]
    elif len(nums) == 3:
        if nums[1] >= 60 or nums[2] >= 60:
            return None
        total_seconds = nums[0] * 3600 + nums[1] * 60 + nums[2]
    else:
        return None
    return total_seconds * 100 + int(frac[:2].ljust(2, "0"))


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

        Site renders the competitors list as div rows (the row wrapper carries
        the ``hover:bg-gray-200`` zebra marker) each holding both a
        ``/persons/{CODE}`` profile link and an ``ID: {numeric}`` token.
        Older layout used ``<tr>`` rows; both are supported.
        """
        mapping: dict[str, int] = {}
        for row in tree.css("tr, div[class*='hover:bg-gray-200']"):
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

        The current site renders the round picker as a ``<select>`` whose
        options carry ``data-link=".../results/{event}/{round}"`` (one per
        (event, round) pair). An older layout carried ``data-event`` /
        ``data-round`` attributes directly; both are supported here so a
        layout regression can't silently break round discovery.
        """
        pairs: list[Tuple[str, int]] = []
        seen: set[Tuple[str, int]] = set()

        for el in tree.css("[data-event][data-round]"):
            event = el.attributes.get("data-event", "")
            try:
                rnd = int(el.attributes.get("data-round", ""))
            except ValueError:
                continue
            if event and (event, rnd) not in seen:
                seen.add((event, rnd))
                pairs.append((event, rnd))

        # Newer markup: the rounded picker lives in a <select data-link=...>.
        for el in tree.css("[data-link]"):
            link = el.attributes.get("data-link", "")
            m = re.search(r"/results/([^/?]+)/(\d+)(?:[?/]|$)", link)
            if not m:
                continue
            event = m.group(1)
            rnd = int(m.group(2))
            if event and (event, rnd) not in seen:
                seen.add((event, rnd))
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
                # Empty result cells are rendered as empty cells holding a bare
                # data-raw-result="0" placeholder; they carry no attempt and must
                # not be stored as a (0, ...) attempt. A real "0.00" could never
                # parse to a raw value of exactly 0, so skip those too.
                if not raw or raw == "0":
                    continue
                try:
                    attempts.append(int(raw))
                except ValueError:
                    continue

            # Best is the fastest non-DNF attempt (centiseconds).
            valid = [a for a in attempts if a >= 0]
            best = min(valid) if valid else None

            # Average: the bold numeric span in the "average" cell. The cell
            # also renders a bold Cyrillic label ("Среднее:") that carries the
            # xl:hidden marker; the LABEL itself is not the number. So pick the
            # first font-bold span whose text is NOT the label, i.e. the one
            # without xl:hidden — that is the actual average text.
            average = None
            for avg_el in entry.css("span.font-bold"):
                txt = (avg_el.text() or "").strip()
                # skip the Cyrillic label; it contains no decimal
                if "Сред" in txt or "Лучш" in txt:
                    continue
                average = _seconds_to_centis(txt)
                if average is not None:
                    break

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
        # The groups page lists every participant once per group as a row that
        # links to their profile via /persons/{RSF}. Current markup renders
        # these rows as divs (no <tr>); older layout used <tr>. The roster we
        # want is the set of DISTINCT participant codes on this round's groups
        # page: that is what the results table is later compared against.
        codes: set[str] = set()
        # Collect the RSF code from EVERY /persons/ link on the page and count
        # distinct codes. A competitor is often listed once per group (and can
        # appear in several groups), so raw link count would over-count; the
        # results table we compare against is keyed on the same distinct RSF
        # codes, so distinct is the value that makes the two match.
        for link in tree.css('a[href*="/persons/"]'):
            href = link.attributes.get("href", "")
            rsf = href.rstrip("/").rsplit("/", 1)[-1]
            if rsf:
                codes.add(rsf)
        return RoundRoster(count=len(codes))

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
