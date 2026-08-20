from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from cubingrf_notifier.notifications.competition_formatter import (
    format_competition_card,
    format_competition_notification,
    format_date_range,
    format_registration_countdown,
    format_registration_reminder,
)
from cubingrf_notifier.bot.competitions import _format_competition


def _comp(
    name="Moscow Open",
    name_en=None,
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
        name_en=name_en,
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
    assert "📍 Moscow" in text
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


def test_notification_cancelled_label_ru():
    comp = _comp(reg_status="cancelled")
    text = format_competition_notification(comp, "ru")
    assert "⛔ Соревнование отменено" in text
    assert "Идёт регистрация" not in text
    assert "Регистрация закрыта" not in text


def test_notification_cancelled_label_en():
    comp = _comp(reg_status="cancelled")
    text = format_competition_notification(comp, "en")
    assert "⛔ Competition cancelled" in text
    assert "Registration is open" not in text


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


# ---------- localized name and city by language ----------

def test_en_uses_english_name_when_available():
    comp = _comp(name="V этап Кубка России 2026", name_en="Russia Speedcubing Cup V 2026")
    text = format_competition_notification(comp, "en")
    assert "Russia Speedcubing Cup V 2026" in text
    assert "V этап Кубка России 2026" not in text


def test_en_falls_back_to_russian_name_without_name_en():
    comp = _comp(name="SPB Muffin Tasting 2026", name_en=None)
    text = format_competition_notification(comp, "en")
    assert "SPB Muffin Tasting 2026" in text


def test_ru_always_uses_russian_name_even_with_name_en():
    comp = _comp(name="V этап Кубка России 2026", name_en="Russia Speedcubing Cup V 2026")
    text = format_competition_notification(comp, "ru")
    assert "V этап Кубка России 2026" in text
    assert "Russia Speedcubing Cup V 2026" not in text


def test_en_uses_english_name_in_reminder_too():
    comp = _comp(
        name="V этап Кубка России 2026",
        name_en="Russia Speedcubing Cup V 2026",
        reg_status="scheduled",
        registration_start_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    text = format_registration_reminder(comp, "en", countdown_at=datetime.now(timezone.utc))
    assert "Russia Speedcubing Cup V 2026" in text
    assert "V этап Кубка России 2026" not in text


def test_en_city_is_localized_on_card():
    comp = _comp(location="Красноярский край, Красноярск")
    text = format_competition_card(comp, "en")
    assert "📍 Krasnoyarsk" in text
    assert "Красноярск" not in text


def test_en_city_uses_conventional_english_name():
    comp = _comp(location="Москва, Москва")
    text = format_competition_card(comp, "en")
    assert "📍 Moscow" in text


def test_ru_city_keeps_russian_name():
    comp = _comp(location="Красноярский край, Красноярск")
    text = format_competition_card(comp, "ru")
    assert "📍 Красноярск" in text
    assert "Krasnoyarsk" not in text


def test_en_city_transliterates_unknown_city():
    comp = _comp(location="Московская область, Мисайлово")
    text = format_competition_card(comp, "en")
    assert "📍 Misailovo" in text


# ---------- registration countdown ----------

def test_countdown_days_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(days=3), "ru", now) == "🟡 Регистрация откроется через 3 дня"
    assert format_registration_countdown(now + timedelta(days=1), "ru", now) == "🟡 Регистрация откроется через 1 день"
    assert format_registration_countdown(now + timedelta(days=2, hours=5), "ru", now) == "🟡 Регистрация откроется через 2 дня"
    assert format_registration_countdown(now + timedelta(days=5), "ru", now) == "🟡 Регистрация откроется через 5 дней"


def test_countdown_days_whole_days_only():
    """A 2.x-day wait shows whole days ('2 дня'), not the next day ('3 дня').

    Regression for VIII этап Кубка России 2026: registration opens 16 Aug
    17:00 Krasnoyarsk (UTC+7) = 16 Aug 10:00 UTC. A few days out the site shows
    'До регистрации 2 дня'; the bot must not round 2 days + hours up to 3.
    """
    now = _utc(2026, 8, 14, 8, 0)  # 2 days 2 hours before opening
    assert format_registration_countdown(_utc(2026, 8, 16, 10, 0), "ru", now) == "🟡 Регистрация откроется через 2 дня"
    assert format_registration_countdown(_utc(2026, 8, 16, 10, 0), "en", now) == "🟡 Registration opens in 2 days"
    # 2 days 23 hours is still "2 days" (whole days), not the next day.
    assert format_registration_countdown(_utc(2026, 8, 16, 10, 0) + timedelta(hours=21), "ru", now) == "🟡 Регистрация откроется через 2 дня"
    # Exactly 3 days -> 3 days.
    assert format_registration_countdown(_utc(2026, 8, 14, 8, 0) + timedelta(days=3), "ru", now) == "🟡 Регистрация откроется через 3 дня"


def test_countdown_hours_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(now + timedelta(hours=5), "ru", now) == "🟡 Регистрация откроется через 5 часов"
    assert format_registration_countdown(now + timedelta(hours=1), "ru", now) == "🟡 Регистрация откроется через 1 час"
    assert format_registration_countdown(now + timedelta(hours=2, minutes=30), "ru", now) == "🟡 Регистрация откроется через 2 часа"


def test_countdown_v_etap_krasnoyarsk_matches_site():
    """Regression: V этап Кубка России 2026 (Krasnoyarsk).

    Registration opens 15 Aug 2026 12:00 (МСК+4, UTC+7) = 15 Aug 05:00 UTC. At
    13:35 UTC on 14 Aug the true wait is 15h25m; cubingrf.org shows 'До
    регистрации 15 часов'. The bot previously rounded up to 16; it must match
    the site and show 15.
    """
    start = _utc(2026, 8, 15, 5, 0)
    now = _utc(2026, 8, 14, 13, 35)
    assert format_registration_countdown(start, "ru", now) == "🟡 Регистрация откроется через 15 часов"
    assert format_registration_countdown(start, "en", now) == "🟡 Registration opens in 15 hours"


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


def test_countdown_rounds_down_en():
    """Hours/minutes round down to whole units, matching cubingrf.org."""
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(minutes=29, seconds=59), "en", now
    ) == "🟡 Registration opens in 29 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=30), "en", now
    ) == "🟡 Registration opens in 30 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=30, seconds=1), "en", now
    ) == "🟡 Registration opens in 30 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=59, seconds=59), "en", now
    ) == "🟡 Registration opens in 59 minutes"
    assert format_registration_countdown(
        now + timedelta(minutes=60), "en", now
    ) == "🟡 Registration opens in 1 hour"
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=59, seconds=59), "en", now
    ) == "🟡 Registration opens in 1 hour"


def test_countdown_rounds_down_ru():
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(minutes=29, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 29 минут"
    assert format_registration_countdown(
        now + timedelta(minutes=59, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 59 минут"
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=59, seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 1 час"


def test_countdown_hour_and_minutes_rounds_down_to_hours():
    """1h30m reads "1 hour": the site never inflates a wait to the next hour."""
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=30), "en", now
    ) == "🟡 Registration opens in 1 hour"
    assert format_registration_countdown(
        now + timedelta(hours=1, minutes=30), "ru", now
    ) == "🟡 Регистрация откроется через 1 час"


def test_countdown_hour_floor_does_not_cross_day_boundary():
    """23h59m stays in hours ("23 часа"), never rounded up to "1 день"."""
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(hours=23, minutes=59), "ru", now
    ) == "🟡 Регистрация откроется через 23 часа"
    assert format_registration_countdown(
        now + timedelta(hours=23, minutes=59), "en", now
    ) == "🟡 Registration opens in 23 hours"
    # Exactly a full day flips to the day band.
    assert format_registration_countdown(
        now + timedelta(days=1), "en", now
    ) == "🟡 Registration opens in 1 day"


def test_countdown_less_than_a_minute_rounds_to_one_minute():
    """Under a minute (but not yet open) must never read 0 minutes."""
    now = _utc(2026, 8, 16, 7, 0)
    assert format_registration_countdown(
        now + timedelta(seconds=30), "en", now
    ) == "🟡 Registration opens in 1 minute"
    assert format_registration_countdown(
        now + timedelta(seconds=59), "ru", now
    ) == "🟡 Регистрация откроется через 1 минуту"


def test_scheduled_card_shows_countdown():
    comp = _comp(
        reg_status="scheduled",
        registration_start_at=datetime.now(timezone.utc) + timedelta(hours=5, minutes=30),
    )
    text = format_competition_card(comp, "ru")
    assert "🟡 Регистрация откроется через 5 часов" in text


def test_scheduled_card_fallback_without_time():
    comp = _comp(reg_status="scheduled", registration_start_at=None)
    text = format_competition_card(comp, "ru")
    assert "🟡 Регистрация скоро откроется" in text
    assert "через" not in text


# ---------- registration-reminder countdown (scheduled instant) ----------

def _scheduled_comp(start):
    return _comp(
        reg_status="scheduled",
        registration_start_at=start,
        date=datetime(2026, 11, 1),
    )


def test_reg_reminder_30_minutes_shows_full_interval_with_scheduler_delay():
    """A 30-minute reminder must read "30 minutes" even when the scheduler
    actually fired a few seconds late (regression for the 29-minutes bug)."""
    start = _utc(2026, 8, 15, 5, 0)
    target = start - timedelta(minutes=30)
    comp = _scheduled_comp(start)

    # What the buggy real-time calculation would produce at execution time:
    late_now = target + timedelta(seconds=5)
    assert format_registration_countdown(start, "en", late_now) == "🟡 Registration opens in 29 minutes"

    # The reminder is measured from its scheduled instant, so the full
    # interval is shown regardless of the few-second scheduler delay.
    assert "Registration opens in 30 minutes" in format_registration_reminder(comp, "en", countdown_at=target)
    assert "Регистрация откроется через 30 минут" in format_registration_reminder(comp, "ru", countdown_at=target)


@pytest.mark.parametrize(
    "interval_min, expected_en, expected_ru",
    [
        (10, "10 minutes", "10 минут"),
        (30, "30 minutes", "30 минут"),
        (60, "1 hour", "1 час"),
        (180, "3 hours", "3 часа"),
        (720, "12 hours", "12 часов"),
        (1440, "1 day", "1 день"),
    ],
)
def test_reg_reminder_countdown_shows_exact_interval(interval_min, expected_en, expected_ru):
    start = _utc(2026, 8, 15, 5, 0)
    target = start - timedelta(minutes=interval_min)
    comp = _scheduled_comp(start)

    text_en = format_registration_reminder(comp, "en", countdown_at=target)
    assert f"Registration opens in {expected_en}" in text_en

    text_ru = format_registration_reminder(comp, "ru", countdown_at=target)
    assert f"Регистрация откроется через {expected_ru}" in text_ru


def test_reg_reminder_delay_of_59_seconds_still_shows_full_interval():
    start = _utc(2026, 8, 15, 5, 0)
    target = start - timedelta(minutes=30)
    comp = _scheduled_comp(start)

    # Worst realistic in-grace delay (misfire_grace_time=60) still understates
    # on the real-time path but the reminder keeps its scheduled value.
    late_now = target + timedelta(seconds=59)
    assert format_registration_countdown(start, "en", late_now) == "🟡 Registration opens in 29 minutes"
    assert "Registration opens in 30 minutes" in format_registration_reminder(comp, "en", countdown_at=target)


def test_competition_page_countdown_logic_unchanged_by_reminder_fix(monkeypatch):
    """The /competitions page countdown is unchanged: it keeps measuring from
    the real current time with floor rounding (matching cubingrf.org), while
    only the reminder path is pinned to its scheduled instant."""
    start = _utc(2026, 8, 15, 5, 0)
    now = _utc(2026, 8, 14, 13, 35)  # 15h25m remaining, site shows "15 часов"

    # Page calculation: floor-of-real-now is untouched.
    assert format_registration_countdown(start, "ru", now) == "🟡 Регистрация откроется через 15 часов"

    # Reminder path: measured from the scheduled instant -> full interval.
    target = start - timedelta(minutes=30)
    reminder = format_registration_reminder(_scheduled_comp(start), "ru", countdown_at=target)
    assert "🟡 Регистрация откроется через 30 минут" in reminder

    # The default page card (no countdown_at) still uses the real clock, not
    # the reminder's scheduled instant.
    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr(
        "cubingrf_notifier.notifications.competition_formatter.datetime",
        FakeDT,
    )
    page_card = format_competition_card(_scheduled_comp(start), "ru")
    assert "🟡 Регистрация откроется через 15 часов" in page_card
    assert "30 минут" not in page_card
