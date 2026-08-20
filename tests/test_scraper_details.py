from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from selectolax.parser import HTMLParser

from cubingrf_notifier.scrapers.cubingrf_html import CubingRFHtmlScraper
from cubingrf_notifier.competitions.models import CompetitionDTO


DETAIL_WITH_EN_NAME = """
<div class="text-lg font-bold mb-4">
    <h2 class="font-semibold text-2xl text-gray-800 leading-tight">
        V этап Кубка России 2026
    </h2>
    <div class="status text-green-700"><i class="fa-solid fa-user-plus"></i> Идёт регистрация</div>
</div>
<div class="text-lg font-bold mb-4">
    <div>Russia Speedcubing Cup V 2026</div>
    <div class="competition-dates">1 ноября 2026</div>
    <div>Красноярск</div>
</div>
"""

DETAIL_WITH_EN_NAME_AND_REG_TEXT = """
<div class="text-lg font-bold mb-4">
    <h2>Phoenix New Facets 2026</h2>
    <div class="status text-blue-700">До регистрации 2 дня</div>
</div>
<div class="text-lg font-bold mb-4">
    <div>Phoenix New Facets 2026</div>
    <div class="competition-dates">20 - 22 ноября 2026</div>
    <div>Москва</div>
</div>
<div>Регистрация участников с 16 августа 2026 10:00 по 22 августа 2026 23:59 (часовой пояс: МСК+0, Москва)</div>
"""

DETAIL_WITHOUT_EN_BLOCK = """
<div class="text-lg font-bold mb-4">
    <h2>Some Competition 2026</h2>
    <div class="status">Завершено</div>
</div>
<p>Регистрация закрыта</p>
"""

DETAIL_EMPTY_EN_DIV = """
<div class="text-lg font-bold mb-4">
    <h2>Some Competition 2026</h2>
</div>
<div class="text-lg font-bold mb-4">
    <div></div>
    <div class="competition-dates">1 ноября 2026</div>
    <div>Москва</div>
</div>
"""


def _scraper():
    return CubingRFHtmlScraper(base_url="https://cubingrf.org/")


def test_extract_english_name_from_detail_page():
    tree = HTMLParser(DETAIL_WITH_EN_NAME)
    assert _scraper()._extract_english_name(tree) == "Russia Speedcubing Cup V 2026"


def test_extract_english_name_returns_none_without_en_block():
    tree = HTMLParser(DETAIL_WITHOUT_EN_BLOCK)
    assert _scraper()._extract_english_name(tree) is None


def test_extract_english_name_skips_empty_en_div():
    tree = HTMLParser(DETAIL_EMPTY_EN_DIV)
    assert _scraper()._extract_english_name(tree) is None


@pytest.mark.asyncio
async def test_fetch_details_returns_reg_text_and_en_name(monkeypatch):
    async def fake_get_page(url):
        return DETAIL_WITH_EN_NAME_AND_REG_TEXT

    scraper = _scraper()
    monkeypatch.setattr(scraper, "_get_page", fake_get_page)
    reg_text, name_en = await scraper._fetch_details("https://cubingrf.org/competitions/X")
    assert "Регистрация участников с" in reg_text
    assert name_en == "Phoenix New Facets 2026"


@pytest.mark.asyncio
async def test_fetch_details_error_returns_empty(monkeypatch):
    async def fake_get_page(url):
        return None

    scraper = _scraper()
    monkeypatch.setattr(scraper, "_get_page", fake_get_page)
    reg_text, name_en = await scraper._fetch_details("https://cubingrf.org/competitions/X")
    assert reg_text == ""
    assert name_en is None


@pytest.mark.asyncio
async def test_enrich_details_sets_name_en_for_all_statuses(monkeypatch):
    scheduled = CompetitionDTO(
        external_id="S",
        name="S 2026",
        url="https://cubingrf.org/competitions/S",
        reg_status="scheduled",
    )
    open_comp = CompetitionDTO(
        external_id="O",
        name="O 2026",
        url="https://cubingrf.org/competitions/O",
        reg_status="open",
    )
    already_localized = CompetitionDTO(
        external_id="L",
        name="L 2026",
        name_en="L 2026 EN",
        url="https://cubingrf.org/competitions/L",
        reg_status="open",
    )

    async def fake_fetch_details(url):
        if "S" in url:
            return "Регистрация участников с 16 августа 2026 10:00 (часовой пояс: МСК+0)", "S 2026 EN"
        if "O" in url:
            return "", "O 2026 EN"
        return "", None  # already localized: not fetched

    calls = []
    real = _scraper()

    async def tracked_fetch_details(url):
        calls.append(url)
        return await fake_fetch_details(url)

    monkeypatch.setattr(real, "_fetch_details", tracked_fetch_details)
    await real._enrich_details([scheduled, open_comp, already_localized])

    assert scheduled.name_en == "S 2026 EN"
    assert open_comp.name_en == "O 2026 EN"
    assert already_localized.name_en == "L 2026 EN"
    assert len(calls) == 2  # the already-localized competition is not re-fetched
    assert scheduled.registration_start_at == datetime(2026, 8, 16, 7, 0, tzinfo=timezone.utc)
    assert open_comp.registration_start_at is None