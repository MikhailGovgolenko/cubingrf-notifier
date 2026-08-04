from typing import Protocol, List
from ..competitions.models import CompetitionDTO

class CompetitionSource(Protocol):
    async def fetch_competitions(self) -> List[CompetitionDTO]:
        """Return list of CompetitionDTO items from the source (HTML or API)."""
        ...
