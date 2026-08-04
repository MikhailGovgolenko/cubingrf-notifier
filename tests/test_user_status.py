from types import SimpleNamespace

from cubingrf_notifier.bot.user_status import format_user_status
from cubingrf_notifier.bot.keyboards import main_menu_keyboard


def _user(notifications_enabled=True, disciplines=()):
    return SimpleNamespace(
        notifications_enabled=notifications_enabled,
        disciplines=[SimpleNamespace(discipline_code=c) for c in disciplines],
    )


def test_status_new_user_defaults():
    text = format_user_status(_user())
    assert "Уведомления: включены ✅" in text
    assert "Регион:\nВсе" in text
    assert "Дисциплины:\nвсе" in text


def test_status_notifications_disabled():
    text = format_user_status(_user(notifications_enabled=False))
    assert "Уведомления: выключены ❌" in text


def test_status_disciplines_labels():
    text = format_user_status(_user(disciplines=["333", "minx", "333bf"]))
    assert "Дисциплины:\n3x3x3, Megaminx, 3x3 Blindfolded" in text


def test_status_disciplines_codes_override_relationship():
    user = _user(disciplines=["333"])
    text = format_user_status(user, discipline_codes=["222"])
    assert "Дисциплины:\n2x2x2" in text


def test_main_menu_has_only_two_actions():
    kb = main_menu_keyboard()
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert buttons == ["📅 Соревнования", "⚙️ Настройки"]