from types import SimpleNamespace

from cubingrf_notifier.bot.user_status import format_user_status
from cubingrf_notifier.bot.keyboards import disciplines_keyboard, main_menu_keyboard
from cubingrf_notifier.competitions.disciplines import DISCIPLINES


def _user(notifications_enabled=True, disciplines=(), regions=()):
    return SimpleNamespace(
        notifications_enabled=notifications_enabled,
        disciplines=[SimpleNamespace(discipline_code=c) for c in disciplines],
        regions=[SimpleNamespace(region_key=r) for r in regions],
    )


def test_status_new_user_defaults():
    text = format_user_status(_user())
    assert "Уведомления: включены ✅" in text
    assert "Язык: Русский" in text
    assert "🌍 Регионы: все" in text
    assert "Дисциплины: все" in text


def test_status_notifications_disabled():
    text = format_user_status(_user(notifications_enabled=False))
    assert "Уведомления: выключены ❌" in text


def test_status_disciplines_labels():
    text = format_user_status(_user(disciplines=["333", "minx", "333bf"]))
    assert "Дисциплины: 3x3x3, Megaminx, 3x3 Blindfolded" in text


def test_status_disciplines_codes_override_relationship():
    user = _user(disciplines=["333"])
    text = format_user_status(user, discipline_codes=["222"])
    assert "Дисциплины: 2x2x2" in text


def test_status_regions_from_relationship():
    text = format_user_status(_user(regions=["Москва", "Санкт-Петербург"]))
    assert "🌍 Регионы: Москва, Санкт-Петербург" in text


def test_status_regions_empty_means_all():
    text = format_user_status(_user(regions=["Москва"]), region_keys=[])
    assert "🌍 Регионы: все" in text


def test_status_english():
    text = format_user_status(_user(), language="en")
    assert "Notifications: enabled ✅" in text
    assert "Language: English" in text
    assert "🌍 Regions: all" in text
    assert "Disciplines: all" in text


def test_main_menu_has_only_two_actions():
    kb = main_menu_keyboard()
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons == ["📅 Соревнования", "⚙️ Настройки"]


def test_main_menu_english():
    kb = main_menu_keyboard(language="en")
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons == ["📅 Competitions", "⚙️ Settings"]


def test_disciplines_keyboard_checkmarks():
    kb = disciplines_keyboard(selected_codes=["333"])
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons[0] == "✅ 3x3x3"
    assert buttons[1] == "⬜ 2x2x2"
    assert all(btn.startswith(("✅ ", "⬜ ")) for btn in buttons[: len(DISCIPLINES)])


def test_disciplines_keyboard_callback_data():
    kb = disciplines_keyboard(selected_codes=[])
    rows = kb.inline_keyboard
    first = rows[0][0]
    assert first.callback_data == "disc:toggle:333"


def test_disciplines_keyboard_vertical_per_row():
    kb = disciplines_keyboard(selected_codes=[])
    rows = kb.inline_keyboard
    for i, (code, _) in enumerate(DISCIPLINES):
        row = rows[i]
        assert len(row) == 1
        assert row[0].callback_data == f"disc:toggle:{code}"