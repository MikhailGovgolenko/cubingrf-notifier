from cubingrf_notifier.i18n import (
    available_languages,
    get_text,
    all_keys_present,
    get_user_language,
    DEFAULT_LANGUAGE,
)


def test_available_languages():
    assert available_languages() == ("ru", "en")


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"


def test_user_language_detects_russian():
    assert get_user_language("ru") == "ru"


def test_user_language_falls_back_to_english():
    assert get_user_language("en") == "en"
    assert get_user_language("de") == "en"
    assert get_user_language("uk") == "en"
    assert get_user_language(None) == "en"
    assert get_user_language("") == "en"


def test_ru_text():
    assert get_text("ru", "menu.competitions") == "📅 Соревнования"
    assert get_text("ru", "settings.language") == "🌐 Язык"


def test_en_text():
    assert get_text("en", "menu.competitions") == "📅 Competitions"
    assert get_text("en", "settings.language") == "🌐 Language"


def test_format_placeholders():
    assert get_text("ru", "competitions.page", page=1, total=3) == "1/3"


def test_unknown_key_falls_back_to_default_then_key():
    assert get_text("ru", "definitely.missing.key") == "definitely.missing.key"


def test_unknown_language_falls_back_to_english():
    assert get_text("zz", "menu.competitions") == "📅 Competitions"


def test_help_localized_differently_in_ru_and_en():
    assert get_text("ru", "help.title") == "📖 Помощь"
    assert get_text("en", "help.title") == "📖 Help"
    assert get_text("ru", "help.title") != get_text("en", "help.title")
    assert "Управляйте" in get_text("ru", "help.intro")
    assert "Control" in get_text("en", "help.intro")


def test_all_keys_present():
    for lang in available_languages():
        assert all_keys_present(lang), f"missing keys for {lang}"