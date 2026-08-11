from types import SimpleNamespace

from cubingrf_notifier.bot.user_status import format_settings_rich
from cubingrf_notifier.bot.keyboards import (
    events_keyboard,
    main_menu_keyboard,
    settings_keyboard,
    notifications_keyboard,
    reminder_intervals_keyboard,
)
from cubingrf_notifier.competitions.disciplines import DISCIPLINES, ALL_DISCIPLINE_CODES
from cubingrf_notifier.competitions.regions import ALL_REGION_KEYS
from cubingrf_notifier.i18n import get_text
from cubingrf_notifier.notifications.competition_formatter import CARD_SEPARATOR
from cubingrf_notifier.notifications.reminder_intervals import REMINDER_INTERVALS


def _user(announcements=True, registrations=True, events=(), regions=()):
    return SimpleNamespace(
        announcements_enabled=announcements,
        registration_notifications_enabled=registrations,
        events=[SimpleNamespace(event_code=c) for c in events],
        regions=[SimpleNamespace(region_key=r) for r in regions],
    )


# ---------- rich settings screen ----------

def test_settings_rich_ru_defaults():
    text = format_settings_rich(_user(), language="ru")
    assert "<h1>⚙️ Настройки</h1>" in text
    assert "<h3>🔔 Уведомления</h3>" in text
    assert "• Анонсы ✅" in text
    assert "• Регистрации ✅" in text
    assert "Регионы</h3>" in text and "Все" in text
    assert "Дисциплины</h3>" in text and "Все" in text
    assert "Язык</h3>" in text and "🇷🇺 Русский" in text


def test_settings_rich_english():
    text = format_settings_rich(_user(), language="en")
    assert "<h1>⚙️ Settings</h1>" in text
    assert "<h3>🔔 Notifications</h3>" in text
    assert "• Announcements ✅" in text
    assert "• Registrations ✅" in text
    assert "Regions</h3>" in text and "All" in text
    assert "Events</h3>" in text and "All" in text
    assert "Language</h3>" in text and "🇬🇧 English" in text


def test_settings_notifications_off_shows_crosses():
    text = format_settings_rich(
        _user(announcements=False, registrations=False),
        language="ru",
    )
    assert "• Анонсы ❌" in text
    assert "• Регистрации ❌" in text


def test_settings_regions_list():
    text = format_settings_rich(
        _user(regions=["Москва", "Санкт-Петербург"]),
        language="ru",
    )
    assert "• Москва" in text
    assert "• Санкт-Петербург" in text


def test_settings_rsf_id_is_separate_block():
    user = SimpleNamespace(
        announcements_enabled=True,
        registration_notifications_enabled=True,
        rsf_id="AS03",
        events=[],
        regions=[],
    )
    text = format_settings_rich(user, language="en")
    # RSF ID is its own <h3> section with its own paragraph…
    assert "<h3>RSF ID</h3>" in text
    assert "<p>• AS03</p>" in text
    # …and is no longer a bullet inside the Notifications block.
    after_notifications = text.split("Notifications</h3>", 1)[1]
    assert "AS03" not in after_notifications.split(CARD_SEPARATOR, 1)[0]


def test_settings_rsf_not_set_shows_hint_separately():
    # rsf omitted entirely -> separate RSF block shows the "not set" hint.
    text = format_settings_rich(_user(), language="en")
    assert "<h3>RSF ID</h3>" in text
    assert get_text("en", "settings.rsf_not_set") in text


def test_settings_all_regions_shows_all():
    user = _user(regions=list(ALL_REGION_KEYS))
    text = format_settings_rich(user, language="ru")
    assert "Регионы</h3>" in text and "Все" in text
    assert "• " not in text.split("Регионы")[1].split(CARD_SEPARATOR)[0]


def test_settings_events_list():
    text = format_settings_rich(_user(events=["333", "minx", "333bf"]), language="ru")
    assert "• 3x3x3" in text
    assert "• Megaminx" in text
    assert "• 3x3 Blindfolded" in text


def test_settings_uses_rich_markup():
    text = format_settings_rich(_user(), language="en")
    assert text.count(CARD_SEPARATOR) == 5
    assert "\n" in text
    # The page title is an <h1>; the first separator comes after it.
    assert text.startswith("<h1>")
    assert text.split("\n", 1)[0] == "<h1>⚙️ Settings</h1>"


# ---------- settings keyboard ----------

def test_settings_keyboard_has_notifications_menu_button():
    kb = settings_keyboard(True, True, "ru")
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔔 Уведомления" in buttons
    assert "🌍 Регионы" in buttons
    assert "🧩 Дисциплины" in buttons
    assert "🌐 Язык" in buttons


def test_notifications_keyboard_toggle_labels():
    kb = notifications_keyboard(False, True, "ru")
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔔 Включить уведомления об анонсах" in texts
    assert "⏰ Выключить уведомления о регистрации" in texts
    assert "⏳ Напоминание о регистрации" in texts


def test_reminder_intervals_keyboard_marks_current():
    kb = reminder_intervals_keyboard(30, "ru")
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any(t.startswith("✅ ") for t in texts)
    assert texts[0] == "⬜ 10 мин"
    assert "✅ 30 мин" in texts


def test_main_menu_has_only_two_actions():
    kb = main_menu_keyboard()
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons == ["📅 Соревнования", "⚙️ Настройки"]


def test_main_menu_english():
    kb = main_menu_keyboard(language="en")
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons == ["📅 Competitions", "⚙️ Settings"]


def test_events_keyboard_checkmarks():
    kb = events_keyboard(selected_codes=["333"])
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons[0] == "✅ 3x3x3"
    assert buttons[1] == "⬜ 2x2x2"
    assert all(btn.startswith(("✅ ", "⬜ ")) for btn in buttons[: len(DISCIPLINES)])


def test_events_keyboard_callback_data():
    kb = events_keyboard(selected_codes=[])
    rows = kb.inline_keyboard
    first = rows[0][0]
    assert first.callback_data == "evt:toggle:333"


def test_events_keyboard_vertical_per_row():
    kb = events_keyboard(selected_codes=[])
    rows = kb.inline_keyboard
    for i, (code, _) in enumerate(DISCIPLINES):
        row = rows[i]
        assert len(row) == 1
        assert row[0].callback_data == f"evt:toggle:{code}"


def test_menu_title_has_no_emoji_prefix():
    for lang in ("ru", "en"):
        title = get_text(lang, "menu.title")
        assert title == "CubingRF Notifier"
