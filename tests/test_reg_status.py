import pytest

from cubingrf_notifier.scrapers.cubingrf_html import CubingRFHtmlScraper


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Идёт регистрация", "open"),
        ("До регистрации 11 дней", "scheduled"),
        ("До регистрации 4 дня", "scheduled"),
        ("Регистрация закрыта", "closed"),
        ("Результаты утверждены", "closed"),
        ("Завершено", "closed"),
        ("Отменены", "cancelled"),
        ("Отменено", "cancelled"),
        ("Что-то неизвестное", None),
        ("", None),
    ],
)
def test_normalize_reg_status(text, expected):
    assert CubingRFHtmlScraper._normalize_reg_status(text) == expected


def test_normalize_reg_status_case_insensitive():
    assert CubingRFHtmlScraper._normalize_reg_status("Идёт РЕГИСТРАЦИЯ") == "open"


def test_normalize_reg_status_cancelled_wins_over_open_text():
    # A cancelled competition must never be labelled as open/closed, even if
    # the card text mixes cancellation with a registration phrase.
    assert CubingRFHtmlScraper._normalize_reg_status("Отменены, идёт регистрация") == "cancelled"


def test_normalize_reg_status_unknown_preserved():
    assert CubingRFHtmlScraper._normalize_reg_status("Ожидайте анонса") is None