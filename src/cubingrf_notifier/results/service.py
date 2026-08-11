"""Orchestrates round-result polling: discovery, polling and notification."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramForbiddenError

from ..config import settings
from ..database.repository import (
    UserRepository,
    CompetitionRepository,
    RoundResultRepository,
)
from .cubingrf import CubingRFResultsScraper
from .logic import (
    is_round_complete,
    snapshot_for,
    hash_snapshot,
    should_poll,
)
from .models import RoundSnapshot

logger = logging.getLogger(__name__)


class RoundResultService:
    """Scans the rounds of competitions entered by eligible users and sends
    per-round result notifications.

    Strategy per poll cycle (the fast job):
      1. Discover the competitions/per-round combos that matter for users who
         opted into round results and have an RSF id.
      2. For each combo, fetch the round results (keeping the roster counts in
         a short-lived cache so the slow groups page isn't re-fetched every
         tick).
      3. Detect when a round becomes complete and notify the new result; on a
         later poll, if the stored hash differs, notify a small "edited" text.
    """

    def __init__(
        self,
        session: AsyncSession,
        scraper: CubingRFResultsScraper | None = None,
        notifier=None,
        base_url: str = "https://cubingrf.org",
    ) -> None:
        self.session = session
        self.scraper = scraper or CubingRFResultsScraper(base_url=base_url)
        self.notifier = notifier
        self.user_repo = UserRepository(session)
        self.comp_repo = CompetitionRepository(session)
        self.rrs_repo = RoundResultRepository(session)
        # {competition_id: (event_code, round_number)} only for entries we
        # still consider "fresh enough" to poll (see ``_active_rounds``).
        self._round_cache: dict[str, list[tuple[str, int]]] = {}
        self._roster_cache: dict[tuple[str, str, int], int] = {}

    # ------------------------------------------------------------------ poll

    async def poll(self) -> list[str]:
        """Run one poll cycle. Returns human-readable tags of what happened
        (used in tests / logs), e.g. ``["new:333/1", "edited:222/1"]``."""
        now = datetime.now(timezone.utc)
        users = await self.user_repo.list_result_tracking_users()
        if not users:
            return []

        events: list[str] = []
        notifier = self.notifier
        for user in users:
            await self._poll_user(user, now, events, notifier)
        await self.session.commit()
        return events

    async def _poll_user(self, user, now: datetime, events: list[str], notifier) -> None:
        # Competitions this user is part of: every competition that already has
        # a round state for them, plus recent competitions they might have
        # joined (registration-window competitors). Filtering here keeps the
        # fast loop from scanning the entire historical competition table.
        tracked_comps = await self.rrs_repo.list_tracked_competition_ids()
        recent_comps = await self._recent_competition_ids()
        candidate_ids = sorted(set(tracked_comps) | set(recent_comps))

        for competition_id in candidate_ids:
            await self._poll_user_competition(user, competition_id, now, events, notifier)

    async def _recent_competition_ids(self) -> list[int]:
        """Competition ids still worth watching, bracketed around today.

        Round results appear during/shortly after an event, so this window
        deliberately ignores registration availability.
        """
        return await self.comp_repo.list_active_competition_ids()

    async def _poll_user_competition(
        self, user, competition_id: int, now, events: list[str], notifier
    ) -> None:
        comp = await self.comp_repo.get_by_id(competition_id)
        if comp is None:
            return
        external_id = comp.external_id

        # Ensure we know which (event, round) combos exist for this comp.
        if external_id not in self._round_cache:
            pairs = await self.scraper.get_round_pairs(external_id)
            self._round_cache[external_id] = pairs

        # The registrant id for the user in this competition, resolved once.
        registrant_id = await self._resolve_registrant_id(user, comp)
        if registrant_id is None:
            # The user isn't a participant here; skip without a state row.
            return

        for event_code, round_number in self._round_cache[external_id]:
            state = await self.rrs_repo.get_or_create_state(
                user.id, competition_id, event_code, round_number
            )
            if not should_poll(
                now=now,
                completed=state.completed,
                completed_at=state.completed_at,
                last_checked_at=state.last_checked_at,
                base_interval=settings.results_poll_interval,
            ):
                continue
            await self._poll_round(
                user, comp, event_code, round_number, registrant_id, state, now, events, notifier
            )
            state.last_checked_at = now

    async def _resolve_registrant_id(self, user, comp) -> Optional[int]:
        """The user's registrant id for ``comp``, or None when not set/participating."""
        rsf = user.rsf_id
        if not rsf:
            return None
        registrant_id = await self.scraper.get_registrant_id(comp.external_id, rsf)
        if registrant_id is None:
            logger.info("RSF id %s not found in competition %s", rsf, comp.external_id)
            return None
        return registrant_id

    async def _poll_round(
        self, user, comp, event_code, round_number, registrant_id, state, now, events, notifier
    ) -> None:
        results = await self.scraper.fetch_round_results(
            comp.external_id, event_code, round_number
        )
        roster_key = (comp.external_id, event_code, round_number)
        if roster_key not in self._roster_cache:
            roster = await self.scraper.fetch_round_roster(
                comp.external_id, event_code, round_number
            )
            self._roster_cache[roster_key] = roster.count

        if not is_round_complete(results, self._roster_cache[roster_key]):
            # Not everyone has a result yet — the round isn't over. When it was
            # previously seen complete (e.g. results briefly undisclosed) we
            # don't un-notify; we simply keep polling on the normal cadence.
            return

        snapshot = snapshot_for(results, registrant_id)
        if snapshot is None:
            # Round finished but this user got no result row (e.g. withdrew).
            if not state.completed:
                state.completed = True
                state.completed_at = now
            return

        digest = hash_snapshot(snapshot)
        if not state.completed:
            state.completed = True
            state.completed_at = now
        if not state.notified:
            await self._notify(user, comp, event_code, round_number, snapshot, edited=False, events=events, notifier=notifier)
            state.notified = True
            state.registrant_id = registrant_id
            state.result_hash = digest
        elif state.result_hash != digest:
            await self._notify(user, comp, event_code, round_number, snapshot, edited=True, events=events, notifier=notifier)
            state.result_hash = digest
            events.append(f"edited:{event_code}/{round_number}")

    async def _notify(
        self, user, comp, event_code, round_number, snapshot, *, edited, events, notifier
    ) -> None:
        notifier = notifier or _make_notifier()
        try:
            await notifier.send_round_result(
                user.telegram_id,
                competition_name=comp.name,
                competition_url=comp.url,
                event_code=event_code,
                round_number=round_number,
                snapshot=snapshot,
                language=user.language or "ru",
                edited=edited,
            )
            events.append(f"{'edited' if edited else 'new'}:{event_code}/{round_number}")
        except TelegramForbiddenError:
            logger.warning("User unreachable (blocked), telegram_id=%s", user.telegram_id)
            await self.user_repo.set_blocked(user.telegram_id)
        except Exception:
            logger.exception(
                "Failed to notify round result user=%s competition=%s event=%s round=%s",
                user.telegram_id, comp.external_id, event_code, round_number,
            )


def _make_notifier():
    from ..notifications.telegram import TelegramNotifier
    return TelegramNotifier()