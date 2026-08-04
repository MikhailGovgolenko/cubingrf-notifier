from typing import List
import httpx
from selectolax.parser import HTMLParser
from ..competitions.models import CompetitionDTO
from .base import CompetitionSource

class CubingRFHtmlScraper(CompetitionSource):
    """Scrapes CubingRF website for competitions using HTML parsing.

    This is an initial implementation and may need adjustment when site
    structure changes.
    """
    BASE_URL = "https://cubingrf.ru/"

    async def fetch_competitions(self) -> List[CompetitionDTO]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.get(self.BASE_URL)
                r.raise_for_status()
            except Exception:
                return []
        tree = HTMLParser(r.text)
        items: List[CompetitionDTO] = []
        # NOTE: site structure may vary; this is a placeholder selector
        for el in tree.css(".competition, .event, .item"):
            title = el.css_first("h3")
            link = el.css_first("a")
            external_id = None
            name = title.text() if title is not None else "Unnamed"
            url = link.attributes.get("href") if link is not None else None
            # Very small best-effort parsing
            external_id = url or name
            items.append(CompetitionDTO(
                external_id=external_id,
                name=name.strip(),
                location=None,
                date=None,
                url=url,
                disciplines=[]
            ))
        return items
