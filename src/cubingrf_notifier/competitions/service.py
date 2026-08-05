from typing import List
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..scrapers.base import CompetitionSource
from ..database.repository import CompetitionRepository
from ..database.models import Competition

logger = logging.getLogger(__name__)


def _dates_differ(current, new) -> bool:
    """True when the stored and freshly parsed date differ.

    Stored values come back timezone-aware from the DB while the parsed DTO
    values are naive, so compare on the bare date to avoid type issues.
    """
    if current is None or new is None:
        return current is not new
    return current.date() != new.date()


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
                continue
            try:
                comp = await self.repo.add_competition(dto)
            except IntegrityError:
                # Lost a race with another run that inserted the same item.
                await self.session.rollback()
                logger.info("Competition %s already stored (race), skipping", dto.external_id)
                continue
            new.append(comp)
            logger.info("Stored new competition %s (%s)", comp.name, dto.external_id)
        return new
