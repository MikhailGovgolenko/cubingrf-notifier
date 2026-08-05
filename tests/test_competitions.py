from datetime import datetime
from types import SimpleNamespace

from cubingrf_notifier.bot.competitions import _format_competition, _format_date


def _comp(
    name="Moscow Open",
    date=datetime(2026, 8, 7),
    location="Москва, Россия",
    disciplines=None,
    reg_status="open",
    url="https://cubingrf.org/competitions/1",
):
    return SimpleNamespace(
        name=name,
        date=date,
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
    assert "📍 Москва, Россия" in text
    assert "🧩 Дисциплины:" in text
    assert "3x3x3, 4x4x4" in text
    assert "🟢 Регистрация открыта" in text
    assert "🔗 https://cubingrf.org/competitions/1" in text


def test_competition_card_scheduled_en():
    text = _format_competition(
        _comp(reg_status="scheduled", disciplines=["333", "333oh"]),
        "en",
    )
    assert "🟡 Registration opens soon" in text
    assert "Disciplines:" in text
    assert "3x3x3, 3x3 One-Handed" in text


def test_competition_card_no_reg_status_line():
    text = _format_competition(_comp(reg_status=None), "ru")
    assert "Регистрация" not in text


def test_competition_card_no_disciplines_section():
    text = _format_competition(_comp(disciplines=None), "ru")
    assert "Дисциплины" not in text