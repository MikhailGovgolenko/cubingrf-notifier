from cubingrf_notifier.competitions.localization import (
    CITY_NAMES,
    localize_city,
    transliterate,
)


def test_transliterate_basic_city():
    assert transliterate("Красноярск") == "Krasnoyarsk"
    assert transliterate("Москва") == "Moskva"
    assert transliterate("Мисайлово") == "Misaylovo"


def test_transliterate_word_endings():
    assert transliterate("Нижний Новгород") == "Nizhny Novgorod"
    assert transliterate("Новый Уренгой") == "Novy Urengoy"
    assert transliterate("Великий Новгород") == "Veliky Novgorod"


def test_transliterate_special_letters():
    assert transliterate("Йошкар-Ола") == "Yoshkar-Ola"
    assert transliterate("Орёл") == "Orel"
    assert transliterate("Санкт-Петербург") == "Sankt-Peterburg"
    assert transliterate("Щёлково") == "Shchelkovo"
    assert transliterate("Мытищи") == "Mytishchi"


def test_transliterate_preserves_latin_and_digits():
    assert transliterate("SPB Muffin 2026") == "SPB Muffin 2026"
    assert transliterate("Москва 77") == "Moskva 77"


def test_localize_city_ru_passthrough():
    assert localize_city("Москва", "ru") == "Москва"
    assert localize_city("Красноярск", "ru") == "Красноярск"
    assert localize_city("Москва", "de") == "Москва"


def test_localize_city_en_uses_curated_map():
    assert localize_city("Москва", "en") == "Moscow"
    assert localize_city("Санкт-Петербург", "en") == "Saint Petersburg"
    assert localize_city("Казань", "en") == "Kazan"
    assert localize_city("Красноярск", "en") == "Krasnoyarsk"
    assert localize_city("нижний новгород", "en") == "Nizhny Novgorod"


def test_localize_city_en_transliterates_unknown():
    assert localize_city("Мисайлово", "en") == "Misailovo"
    assert localize_city("Кашира", "en") == "Kashira"


def test_localize_city_en_empty_and_latin():
    assert localize_city("", "en") == ""
    assert localize_city("SPB", "en") == "SPB"


def test_curated_map_has_no_duplicate_lowercase_keys():
    keys = [k for k in CITY_NAMES if k != k.strip().lower()]
    assert keys == []
    assert len(CITY_NAMES) == len(set(CITY_NAMES))