from datetime import datetime
from types import SimpleNamespace

from cubingrf_notifier.bot.competitions import (
    _format_competition,
    _format_date,
    _format_date_range,
    _format_competitions,
    CARD_SEPARATOR,
)
from cubingrf_notifier.bot.keyboards import competitions_keyboard
from cubingrf_notifier.competitions.disciplines import ALL_DISCIPLINE_CODES


def _comp(
    name="Moscow Open",
    date=datetime(2026, 8, 7),
    end_date=None,
    location="Москва, Москва",
    disciplines=None,
    reg_status="open",
    url="https://cubingrf.org/competitions/1",
):
    return SimpleNamespace(
        name=name,
        date=date,
        end_date=end_date,
        location=location,
        disciplines=disciplines or [],
        reg_status=reg_status,
        url=url,
    )


def test_format_date_ru():
    assert _format_date(datetime(2026, 8, 7), "ru") == "7 августа 2026"


def test_format_date_en():
    assert _format_date(datetime(2026, 8, 7), "en") == "7 August 2026"


def test_format_date_unknown():
    assert _format_date(None, "ru") == "дата неизвестна"


def test_competition_card_ru_open():
    text = _format_competition(_comp(disciplines=["333", "444"]), "ru")
    assert "🏆 Moscow Open" in text
    assert "📆 7 августа 2026" in text
    assert "📍 Москва" in text
    assert "🧩 3x3 • 4x4" in text
    assert "🟢 Идёт регистрация" in text
    assert "🔗 https://cubingrf.org/competitions/1" in text


def test_competition_card_scheduled_en():
    text = _format_competition(
        _comp(reg_status="scheduled", disciplines=["333", "333oh"]),
        "en",
    )
    assert "🟡 Registration opens soon" in text
    assert "🧩 3x3 • OH" in text


def test_competition_card_no_reg_status_line():
    text = _format_competition(_comp(reg_status=None), "ru")
    assert "Регистрация" not in text


def test_competition_card_no_disciplines_section():
    text = _format_competition(_comp(disciplines=None), "ru")
    assert "Дисциплины" not in text


def test_competition_card_all_disciplines_listed():
    text = _format_competition(_comp(disciplines=["333", "222", "444", "555", "666", "777"]), "ru")
    assert "🧩 3x3 • 2x2 • 4x4 • 5x5 • 6x6 • 7x7" in text
    assert "+" not in text.split("🧩")[1]


def test_card_disciplines_follow_catalog_order():
    shuffled = ["333mbf", "sq1", "333", "pyram", "clock", "555bf"]
    text = _format_competition(_comp(disciplines=shuffled), "ru")
    labels = [ALL_DISCIPLINE_CODES]  # catalog order is the single source
    assert "🧩 3x3 • Clock • Pyraminx • Square-1 • 5BLD • MBLD" in text


def test_date_range_single_day():
    d = datetime(2026, 8, 7)
    assert _format_date_range(d, None, "ru") == "7 августа 2026"
    assert _format_date_range(d, d, "ru") == "7 августа 2026"
    assert _format_date_range(d, datetime(2026, 8, 6), "ru") == "7 августа 2026"


def test_date_range_same_month():
    start = datetime(2026, 12, 4)
    end = datetime(2026, 12, 6)
    assert _format_date_range(start, end, "ru") == "4–6 декабря 2026"
    assert _format_date_range(start, end, "en") == "4–6 December 2026"


def test_date_range_cross_month():
    start = datetime(2026, 12, 28)
    end = datetime(2027, 1, 3)
    assert _format_date_range(start, end, "ru") == "28 декабря 2026 — 3 января 2027"
    assert _format_date_range(start, end, "en") == "28 December 2026 — 3 January 2027"


def test_competition_card_date_range_shown():
    text = _format_competition(
        _comp(date=datetime(2026, 12, 4), end_date=datetime(2026, 12, 6)),
        "ru",
    )
    assert "📆 4–6 декабря 2026" in text


def test_competition_card_single_date_unchanged():
    text = _format_competition(_comp(date=datetime(2026, 8, 7), end_date=None), "ru")
    assert "📆 7 августа 2026" in text


def test_competition_card_city_only_location():
    text = _format_competition(_comp(location="Московская область, Щёлково"), "ru")
    assert "📍 Щёлково" in text


def test_format_competitions_full_width_separator():
    comps = [_comp(name="A"), _comp(name="B")]
    text = _format_competitions(comps, "ru")
    assert CARD_SEPARATOR in text
    assert "---" not in text


def test_format_competitions_shows_matching_count():
    comps = [_comp(name="A"), _comp(name="B")]
    text = _format_competitions(comps, "ru", total_count=12)
    assert "📊 Подходит соревнований: 12" in text


def test_competitions_keyboard_single_page_hides_indicator():
    kb = competitions_keyboard(0, 1, "ru")
    buttons = [b.text for row in kb.inline_keyboard for b in row]
    assert buttons == ["◀️ Назад"]


def test_competitions_keyboard_multi_page_shows_page():
    kb = competitions_keyboard(1, 3, "ru")
    texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "⬅️" in texts
    assert "2/3" in texts
    assert "➡️" in texts