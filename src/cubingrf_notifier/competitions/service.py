from typing import List
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..scrapers.base import CompetitionSource
from ..database.repository import CompetitionRepository
from ..database.models import Competition

logger = logging.getLogger(__name__)

_CANCELLED = "cancelled"


def _mark_cancelled_once(comp: Competition, now: datetime | None = None) -> bool:
    """Stamp the cancellation moment the first time a competition is seen as
    cancelled.

    Sets ``comp.cancelled_at`` to ``now`` only when the competition is marked
    cancelled and has no timestamp yet, so repeated scraper runs never reset
    the 24-hour grace window. This also covers competitions that were already
    cancelled before this feature shipped: their first scrape after upgrade
    records a fresh timestamp, giving them a full 24-hour window from then.
    Returns True when a timestamp was newly written.
    """
    if comp.reg_status != _CANCELLED or comp.cancelled_at is not None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    comp.cancelled_at = now
    return True


def _dates_differ(current, new) -> bool:
    """True when the stored and freshly parsed date differ.

    Stored values come back timezone-aware from the DB while the parsed DTO
    values are naive, so compare on the bare date to avoid type issues.
    """
    if current is None or new is None:
        return current is not new
    return current.date() != new.date()


def _start_at_differ(current, new) -> bool:
    """True when the stored and freshly parsed registration start differ.

    Both values are tz-aware; compare instants in UTC.
    """
    if current is None or new is None:
        return current is not new
    if current.tzinfo is None or new.tzinfo is None:
        return current != new
    return current.astimezone(timezone.utc) != new.astimezone(timezone.utc)


class CompetitionService:
    """Business logic for competitions. Decoupled from the data source."""

    def __init__(self, source: CompetitionSource, session: AsyncSession):
        self.source = source
        self.repo = CompetitionRepository(session)

    async def check_new_competitions(self) -> List[Competition]:
        """Fetch competitions from source, persist the new ones.

        Existing competitions have their registration status refreshed so the
        "open / scheduled / closed" filter always reflects the current site.
        Returns the newly persisted Competition ORM objects (with their real
        database ids) so callers can reference them in notifications.
        """
        found = await self.source.fetch_competitions()
        new: List[Competition] = []
        for dto in found:
            existing = await self.repo.get_by_external_id(dto.external_id)
            if existing is not None:
                if existing.reg_status != dto.reg_status:
                    existing.reg_status = dto.reg_status
                    logger.info(
                        "Updated reg_status for %s (%s): %s",
                        existing.name,
                        existing.external_id,
                        dto.reg_status,
                    )
                if _mark_cancelled_once(existing):
                    logger.info(
                        "Competition %s (%s) marked cancelled at %s",
                        existing.name,
                        existing.external_id,
                        existing.cancelled_at,
                    )
                if _dates_differ(existing.date, dto.date) or _dates_differ(existing.end_date, dto.end_date):
                    existing.date = dto.date
                    existing.end_date = dto.end_date
                    logger.info(
                        "Updated dates for %s (%s): %s - %s",
                        existing.name,
                        existing.external_id,
                        dto.date,
                        dto.end_date,
                    )
                if _start_at_differ(existing.registration_start_at, dto.registration_start_at):
                    existing.registration_start_at = dto.registration_start_at
                    logger.info(
                        "Updated registration start for %s (%s): %s",
                        existing.name,
                        existing.external_id,
                        dto.registration_start_at,
                    )
                if dto.name_en and existing.name_en != dto.name_en:
                    existing.name_en = dto.name_en
                    logger.info(
                        "Updated English name for %s (%s): %s",
                        existing.name,
                        existing.external_id,
                        dto.name_en,
                    )
                continue
            try:
                comp = await self.repo.add_competition(dto)
            except IntegrityError:
                # Lost a race with another run that inserted the same item.
                await self.session.rollback()
                logger.info("Competition %s already stored (race), skipping", dto.external_id)
                continue
            if _mark_cancelled_once(comp):
                logger.info(
                    "Competition %s (%s) stored already cancelled at %s",
                    comp.name,
                    dto.external_id,
                    comp.cancelled_at,
                )
            new.append(comp)
            logger.info("Stored new competition %s (%s)", comp.name, dto.external_id)
        return new
