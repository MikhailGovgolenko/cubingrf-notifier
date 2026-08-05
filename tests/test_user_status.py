from types import SimpleNamespace

from cubingrf_notifier.bot.user_status import format_user_status
from cubingrf_notifier.bot.keyboards import events_keyboard, main_menu_keyboard
from cubingrf_notifier.competitions.disciplines import DISCIPLINES, ALL_DISCIPLINE_CODES
from cubingrf_notifier.competitions.regions import ALL_REGION_KEYS
from cubingrf_notifier.i18n import get_text


def _user(notifications_enabled=True, events=(), regions=()):
    return SimpleNamespace(
        notifications_enabled=notifications_enabled,
        events=[SimpleNamespace(event_code=c) for c in events],
        regions=[SimpleNamespace(region_key=r) for r in regions],
    )


def test_status_new_user_defaults():
    text = format_user_status(_user(), language="ru")
    assert "Уведомления: ✅" in text
    assert "Язык: 🇷🇺 Русский" in text
    assert "Регионы: Все" in text
    assert "Дисциплины: Все" in text


def test_status_notifications_disabled():
    text = format_user_status(_user(notifications_enabled=False), language="ru")
    assert "Уведомления: ❌" in text


def test_status_disciplines_labels():
    text = format_user_status(_user(events=["333", "minx", "333bf"]), language="ru")
    assert "Дисциплины:" in text
    assert "• 3x3x3" in text
    assert "• Megaminx" in text
    assert "• 3x3 Blindfolded" in text


def test_status_disciplines_codes_override_relationship():
    user = _user(events=["333"])
    text = format_user_status(user, event_codes=["222"], language="ru")
    assert "• 2x2x2" in text
    assert "3x3x3" not in text


def test_status_all_disciplines_shows_all_ru():
    user = _user(events=list(ALL_DISCIPLINE_CODES))
    text = format_user_status(user, language="ru")
    assert "Дисциплины: Все" in text
    assert "• " not in text


def test_status_all_disciplines_shows_all_en():
    user = _user(events=list(ALL_DISCIPLINE_CODES))
    text = format_user_status(user, language="en")
    assert "Events: All" in text
    assert "• " not in text


def test_status_partial_disciplines_lists_selection():
    user = _user(events=["333", "minx", "clock"])
    text = format_user_status(user, language="ru")
    assert "Дисциплины: Все" not in text
    assert "Дисциплины:" in text


def test_status_discipline_labels_follow_catalog_order():
    user = _user(events=["minx", "333", "clock"])
    text = format_user_status(user, language="ru")
    disci = text.split("Дисциплины:", 1)[1]
    labels = [name for name in ("3x3x3", "Clock", "Megaminx") if f"• {name}" in disci]
    assert labels == ["3x3x3", "Clock", "Megaminx"]
    assert disci.index("• 3x3x3") < disci.index("• Clock") < disci.index("• Megaminx")


def test_status_regions_from_relationship():
    text = format_user_status(_user(regions=["Москва", "Санкт-Петербург"]), language="ru")
    assert "Регионы:" in text
    assert "• Москва" in text
    assert "• Санкт-Петербург" in text


def test_status_regions_empty_means_all():
    text = format_user_status(_user(regions=["Москва"]), region_keys=[], language="ru")
    assert "Регионы: Все" in text


def test_status_all_regions_shows_all_ru():
    user = _user(regions=list(ALL_REGION_KEYS))
    text = format_user_status(user, language="ru")
    assert "Регионы: Все" in text
    assert "• " not in text


def test_status_all_regions_shows_all_en():
    user = _user(regions=list(ALL_REGION_KEYS))
    text = format_user_status(user, language="en")
    assert "Regions: All" in text
    assert "• " not in text


def test_status_single_region_shows_name():
    user = _user(regions=["Москва"])
    text = format_user_status(user, language="ru")
    assert "Регионы: Все" not in text
    assert "• Москва" in text


def test_status_few_regions_shows_list_in_catalog_order():
    user = _user(regions=["Омская область", "Москва", "Республика Коми"])
    text = format_user_status(user, language="ru")
    assert "Регионы: Все" not in text
    assert "Регионы:" in text
    assert "• Москва" in text
    assert "• Омская область" in text
    assert "• Республика Коми" in text
    assert text.index("• Москва") < text.index("• Омская область") < text.index("• Республика Коми")


def test_status_english():
    text = format_user_status(_user(), language="en")
    assert "Notifications: ✅" in text
    assert "Language: 🇬🇧 English" in text
    assert "Regions: All" in text
    assert "Events: All" in text


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