from typing import List
from ..scrapers.base import CompetitionSource
from ..database.repository import Repository
from ..competitions.models import CompetitionDTO
from sqlalchemy.ext.asyncio import AsyncSession

class CompetitionService:
    """Business logic for competitions. Decoupled from data source."""
    def __init__(self, source: CompetitionSource, session: AsyncSession):
        self.source = source
        self.repo = Repository(session)

    async def check_new_competitions(self) -> List[CompetitionDTO]:
        """Fetch from source, persist new competitions, return new items."""
        found: List[CompetitionDTO] = await self.source.fetch_competitions()
        new: List[CompetitionDTO] = []
        for dto in found:
            existing = await self.repo.get_competition_by_external_id(dto.external_id)
            if existing is None:
                comp = await self.repo.add_competition(dto)
                new.append(dto)
        return new
