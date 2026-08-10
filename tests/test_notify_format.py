from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cubingrf_notifier.notifications.competition_formatter import (
    format_competition_card,
    format_competition_notification,
    format_date_range,
    format_registration_countdown,
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
    registration_start_at=None,
):
    return SimpleNamespace(
        name=name,
        date=date,
        end_date=end_date,
        location=location,
        disciplines=list(disciplines),
        reg_status=reg_status,
        url=url,
        registration_start_at=registration_start_at,
    )


def _utc(*args, **kwargs):
    return datetime(*args, tzinfo=timezone.utc, **kwargs)


def test_notification_ru_all_fields():
    text = format_competition_notification(_comp(), "ru")
    assert "🆕 Новое соревнование!" in text
    assert '<b><a href="https://cubingrf.org/competitions/1">Moscow Open</a></b>' in text
    assert "📅 7 августа 2026" in text
    assert "📍 Москва" in text
    assert "🧩 3x3 • 4x4" in text
    assert "🟢 Идёт регистрация" in text
    assert "🔗 " not in text


def test_notification_en_all_fields():
    text = format_competition_notification(_comp(), "en")
    assert "🆕 New competition!" in text
    assert '<b><a href="https://cubingrf.org/competitions/1">Moscow Open</a></b>' in text
    assert "📅 7 August 2026" in text
    assert "📍 Москва" in text
    assert "🧩 3x3 • 4x4" in text
    assert "🟢 Registration is open" in text
    assert "🔗 " not in text


def test_notification_contains_card():
    comp = _comp()
    card = format_competition_card(comp, "ru")
    notif = format_competition_notification(comp, "ru")
    assert notif == f"<h1>🆕 Новое соревнование!</h1>\n<p>{card}</p>"


def test_notification_matches_competition_page_card():
    comp = _comp()
    assert format_competition_notification(comp, "ru").endswith(
        f"<p>{_format_competition(comp, 'ru')}</p>"
    )


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


# ---------- title link ----------

def test_title_is_html_link():
    text = format_competition_card(_comp(), "ru")
    assert '<b><a href="https://cubingrf.org/competitions/1">Moscow Open</a></b>' in text
    assert "🔗" not in text


def test_title_without_url_is_plain():
    text = format_competition_card(_comp(url=None), "ru")
    assert "🏆 <b>Moscow Open</b>" in text
    assert "[" not in text.split("🏆")[1]


def test_title_escapes_html_specials():
    comp = _comp(name="SPB <Cup> & Test", url="https://cubingrf.org/competitions/X")
    text = format_competition_card(comp, "ru")
    assert "SPB &lt;Cup&gt; &amp; Test" in text


def test_title_preserves_markdown_specials():
    comp = _comp(name="SPB *Cup* [test] (2026)", url="https://cubingrf.org/competitions/X")
    text = format_competition_card(comp, "ru")
    assert "SPB *Cup* [test] (2026)" in text


def test_title_keeps_underscore_in_name():
    comp = _comp(name="The _Best_ Comp", url="https://cubingrf.org/competitions/Y")
    text = format_competition_card(comp, "ru")
    assert ">The _Best_ Comp<" in text


def test_title_link_used_in_notifications_too():
    text = format_competition_notification(_comp(), "ru")
    assert '<a href="https://cubingrf.org/competitions/1">Moscow Open</a>' in text


# ---------- registration countdown ----------

def test_countdown_days_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(days=3), "ru", now) == "🟡 Регистрация откроется через 3 дня"
    assert format_registration_countdown(now + timedelta(days=1), "ru", now) == "🟡 Регистрация откроется через 1 день"
    assert format_registration_countdown(now + timedelta(days=2, hours=5), "ru", now) == "🟡 Регистрация откроется через 3 дня"
    assert format_registration_countdown(now + timedelta(days=5), "ru", now) == "🟡 Регистрация откроется через 5 дней"


def test_countdown_hours_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(hours=5), "ru", now) == "🟡 Регистрация откроется через 5 часов"
    assert format_registration_countdown(now + timedelta(hours=1), "ru", now) == "🟡 Регистрация откроется через 1 час"
    assert format_registration_countdown(now + timedelta(hours=2, minutes=30), "ru", now) == "🟡 Регистрация откроется через 3 часа"


def test_countdown_minutes_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(minutes=30), "ru", now) == "🟡 Регистрация откроется через 30 минут"
    assert format_registration_countdown(now + timedelta(minutes=1), "ru", now) == "🟡 Регистрация откроется через 1 минуту"
    assert format_registration_countdown(now + timedelta(minutes=2), "ru", now) == "🟡 Регистрация откроется через 2 минуты"


def test_countdown_en():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(days=3), "en", now) == "🟡 Registration opens in 3 days"
    assert format_registration_countdown(now + timedelta(days=1), "en", now) == "🟡 Registration opens in 1 day"
    assert format_registration_countdown(now + timedelta(hours=5), "en", now) == "🟡 Registration opens in 5 hours"
    assert format_registration_countdown(now + timedelta(minutes=30), "en", now) == "🟡 Registration opens in 30 minutes"
    assert format_registration_countdown(now + timedelta(minutes=1), "en", now) == "🟡 Registration opens in 1 minute"


def test_countdown_no_time_returns_none():
    assert format_registration_countdown(None, "ru") is None


def test_countdown_past_or_zero_returns_none():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now - timedelta(minutes=5), "ru", now) is None
    assert format_registration_countdown(now, "ru", now) is None


def test_countdown_rounds_up_en():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(minutes=29, seconds=59), "en", now
    ) == "🟡 Registration opens in 30 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=30), "en", now
    ) == "🟡 Registration opens in 30 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=30, seconds=1), "en", now
    ) == "🟡 Registration opens in 31 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=59, seconds=59), "en", now
    ) == "🟡 Registration opens in 1 hour"
    assert format_registration_countdown(
        now + timedelta(minutes=60), "en", now
    ) == "🟡 Registration opens in 1 hour"
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=59, seconds=59), "en", now
    ) == "🟡 Registration opens in 2 hours"


def test_countdown_rounds_up_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(minutes=29, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 30 минут"
    assert format_registration_countdown(
        now + timedelta(minutes=59, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 1 час"
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=59, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 2 часа"


def test_scheduled_card_shows_countdown():
    comp = _comp(
        reg_status="scheduled",
        registration_start_at=datetime.now(timezone.utc) + timedelta(hours=5, minutes=30),
    )
    text = format_competition_card(comp, "ru")
    assert "🟡 Регистрация откроется через 6 часов" in text


def test_scheduled_card_fallback_without_time():
    comp = _comp(reg_status="scheduled", registration_start_at=None)
    text = format_competition_card(comp, "ru")
    assert "🟡 Регистрация скоро откроется" in text
    assert "через" not in text
