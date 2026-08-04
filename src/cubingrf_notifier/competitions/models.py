from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CompetitionDTO:
    external_id: str
    name: str
    location: Optional[str]
    date: Optional[str]
    url: Optional[str]
    disciplines: List[str]
