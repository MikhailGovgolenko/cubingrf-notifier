from typing import List
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..scrapers.base import CompetitionSource
from ..database.repository import CompetitionRepository
from ..database.models import Competition

logger = logging.getLogger(__name__)


class CompetitionService:
    """Business logic for competitions. Decoupled from the data source."""

    def __init__(self, source: CompetitionSource, session: AsyncSession):
        self.source = source
        self.repo = CompetitionRepository(session)

    async def check_new_competitions(self) -> List[Competition]:
        """Fetch competitions from source, persist the new ones.

        Returns the newly persisted Competition ORM objects (with their real
        database ids) so callers can reference them in notifications.
        """
        found = await self.source.fetch_competitions()
        new: List[Competition] = []
        for dto in found:
            if await self.repo.exists_by_external_id(dto.external_id):
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
