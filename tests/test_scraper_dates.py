from datetime import datetime

from cubingrf_notifier.scrapers.cubingrf_html import parse_russian_date, parse_russian_date_range


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