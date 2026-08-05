from datetime import datetime, timezone

from cubingrf_notifier.scrapers.cubingrf_html import parse_russian_date, parse_russian_date_range, parse_registration_start


def test_parse_single_date():
    assert parse_russian_date("22 августа 2026") == datetime(2026, 8, 22)
    assert parse_russian_date_range("22 августа 2026") == (datetime(2026, 8, 22), None)


def test_parse_same_month_range_hyphen():
    start, end = parse_russian_date_range("7 - 9 августа 2026")
    assert start == datetime(2026, 8, 7)
    assert end == datetime(2026, 8, 9)


def test_parse_same_month_range_dash_and_en_dash():
    assert parse_russian_date_range("7–9 августа 2026") == (
        datetime(2026, 8, 7),
        datetime(2026, 8, 9),
    )
    assert parse_russian_date_range("7—9 августа 2026") == (
        datetime(2026, 8, 7),
        datetime(2026, 8, 9),
    )


def test_parse_cross_month_range():
    start, end = parse_russian_date_range("28 декабря 2026 - 3 января 2027")
    assert start == datetime(2026, 12, 28)
    assert end == datetime(2027, 1, 3)


def test_parse_range_word_dо():
    start, end = parse_russian_date_range("28 декабря 2026 до 3 января 2027")
    assert start == datetime(2026, 12, 28)
    assert end == datetime(2027, 1, 3)


def test_parse_empty_and_garbage():
    assert parse_russian_date_range("") == (None, None)
    assert parse_russian_date_range("совершенно не дата") == (None, None)


def test_parse_registration_start_msk_zero():
    text = (
        "Регистрация участников с 16 августа 2026 10:00 по 3 ноября 2026 20:00 "
        "(часовой пояс: МСК+0, московское время)."
    )
    assert parse_registration_start(text) == datetime(2026, 8, 16, 7, 0, tzinfo=timezone.utc)


def test_parse_registration_start_msk_plus_four():
    text = (
        "Регистрация участников с 15 августа 2026 12:00 по 23 октября 2026 20:00 "
        "(часовой пояс: МСК+4, красноярское время)."
    )
    assert parse_registration_start(text) == datetime(2026, 8, 15, 5, 0, tzinfo=timezone.utc)


def test_parse_registration_start_no_time_returns_none():
    text = "Регистрация участников с 16 августа 2026 по 3 ноября 2026 (часовой пояс: МСК+0)."
    assert parse_registration_start(text) is None


def test_parse_registration_start_garbage_returns_none():
    assert parse_registration_start("") is None
    assert parse_registration_start("совершенно не про регистрацию") is None
    assert parse_registration_start(None) is None