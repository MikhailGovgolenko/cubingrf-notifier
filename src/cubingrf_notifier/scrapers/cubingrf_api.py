from typing import List
from ..competitions.models import CompetitionDTO
from .base import CompetitionSource

class CubingRFApiClient(CompetitionSource):
    """Placeholder API client for future CubingRF API.

    Current implementation is a stub that raises NotImplementedError.
    """
    async def fetch_competitions(self) -> List[CompetitionDTO]:
        raise NotImplementedError("API client not yet implemented")
