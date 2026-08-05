from datetime import datetime
from types import SimpleNamespace

from cubingrf_notifier.notifications.competition_formatter import (
    format_competition_card,
    format_competition_notification,
    format_date_range,
)
from cubingrf_notifier.bot.competitions import _format_competition


def _comp(
    name="Moscow Open",
    date=datetime(2026, 8, 7),
    end_date=None,
    location="Москва, Москва",
    disciplines=("333", "444"),
    reg_status="open",
    url="https://cubingrf.org/competitions/1",
):
    return SimpleNamespace(
        name=name,
        date=date,
        end_date=end_date,
        location=location,
        disciplines=list(disciplines),
        reg_status=reg_status,
        url=url,
    )


def test_notification_ru_all_fields():
    text = format_competition_notification(_comp(), "ru")
    assert "🆕 Новое соревнование!" in text
    assert "🏆 Moscow Open" in text
    assert "📅 7 августа 2026" in text
    assert "📍 Москва" in text
    assert "🧩 3x3 • 4x4" in text
    assert "🟢 Идёт регистрация" in text
    assert "🔗 https://cubingrf.org/competitions/1" in text


def test_notification_en_all_fields():
    text = format_competition_notification(_comp(), "en")
    assert "🆕 New competition!" in text
    assert "🏆 Moscow Open" in text
    assert "📅 7 August 2026" in text
    assert "📍 Москва" in text
    assert "🧩 3x3 • 4x4" in text
    assert "🟢 Registration is open" in text
    assert "🔗 https://cubingrf.org/competitions/1" in text


def test_notification_contains_card():
    comp = _comp()
    card = format_competition_card(comp, "ru")
    notif = format_competition_notification(comp, "ru")
    assert notif == f"🆕 Новое соревнование!\n\n{card}"


def test_notification_matches_competition_page_card():
    comp = _comp()
    assert format_competition_notification(comp, "ru").endswith(_format_competition(comp, "ru"))


def test_notification_date_range():
    comp = _comp(date=datetime(2026, 12, 4), end_date=datetime(2026, 12, 6))
    text = format_competition_notification(comp, "ru")
    assert "📅 4–6 декабря 2026" in text


def test_notification_no_disciplines_omits_line():
    comp = _comp(disciplines=[])
    text = format_competition_notification(comp, "ru")
    assert "Дисциплины" not in text
    assert "🧩" not in text.split("📅")[1]


def test_notification_scheduled_registration():
    comp = _comp(reg_status="scheduled")
    assert "🟡" in format_competition_notification(comp, "ru")
    assert "Registration opens soon" in format_competition_notification(comp, "en")


def test_notification_closed_registration():
    comp = _comp(reg_status="closed")
    assert "🔴" in format_competition_notification(comp, "ru")


def test_notification_unknown_registration_no_line():
    comp = _comp(reg_status=None)
    text = format_competition_notification(comp, "ru")
    assert "Регистрация" not in text


def test_date_range_localized_both_langs():
    start, end = datetime(2026, 12, 28), datetime(2027, 1, 3)
    assert format_date_range(start, end, "ru") == "28 декабря 2026 — 3 января 2027"
    assert format_date_range(start, end, "en") == "28 December 2026 — 3 January 2027"
