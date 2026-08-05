from cubingrf_notifier.i18n import (
    available_languages,
    get_text,
    all_keys_present,
    DEFAULT_LANGUAGE,
)


def test_available_languages():
    assert available_languages() == ("ru", "en")


def test_default_language_is_russian():
    assert DEFAULT_LANGUAGE == "ru"


def test_ru_text():
    assert get_text("ru", "menu.competitions") == "📅 Соревнования"
    assert get_text("ru", "settings.language") == "🌐 Язык"


def test_en_text():
    assert get_text("en", "menu.competitions") == "📅 Competitions"
    assert get_text("en", "settings.language") == "🌐 Language"


def test_format_placeholders():
    assert get_text("ru", "competitions.page", page=1, total=3) == "Страница 1/3"


def test_unknown_key_falls_back_to_default_then_key():
    assert get_text("ru", "definitely.missing.key") == "definitely.missing.key"


def test_unknown_language_falls_back_to_ru():
    assert get_text("zz", "menu.competitions") == "📅 Соревнования"


def test_all_keys_present():
    for lang in available_languages():
        assert all_keys_present(lang), f"missing keys for {lang}"