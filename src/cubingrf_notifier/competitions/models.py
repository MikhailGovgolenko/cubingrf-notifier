from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CompetitionDTO:
    external_id: str
    name: str
    location: Optional[str] = None
    date: Optional[datetime] = None
    url: Optional[str] = None
    disciplines: List[str] = field(default_factory=list)
    # Registration availability: 'open' | 'scheduled' | 'closed' | None (unknown).
    reg_status: Optional[str] = None
