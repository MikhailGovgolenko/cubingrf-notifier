from cubingrf_notifier.results.models import RoundSnapshot
from cubingrf_notifier.results.formatter import format_time, format_attempts, format_round_result


def test_format_time_seconds():
    assert format_time(913, "en") == "9.13"


def test_format_time_whole_seconds():
    assert format_time(900, "en") == "9.00"


def test_format_time_dnf():
    assert format_time(-1, "en") == "DNF"


def test_format_time_none():
    assert format_time(None, "en") == "-"


def test_format_attempts():
    snap = RoundSnapshot(attempts=(912, 888, 845, 930, 855))
    assert format_attempts(snap, "en") == "9.12, 8.88, 8.45, 9.30, 8.55"


def test_format_attempts_empty():
    snap = RoundSnapshot(attempts=())
    assert format_attempts(snap, "en") is None


def test_format_round_result_new_includes_all_fields():
    snap = RoundSnapshot(
        place=3,
        attempts=(912, 888, 845, 930, 855),
        average=886,
        best=845,
        advanced=True,
    )
    text = format_round_result(
        "SPB Test",
        "https://cubingrf.org/competitions/SPBTest",
        "333",
        2,
        snap,
        language="en",
    )
    assert "Your round result" in text
    assert "3x3x3" in text
    assert "Place: 3" in text
    assert "9.12, 8.88, 8.45, 9.30, 8.55" in text
    assert "Average: 8.86" in text
    assert "Best: 8.45" in text
    assert "advanced to the next round" in text
    assert "SPB Test" in text


def test_format_round_result_layout_blank_lines():
    snap = RoundSnapshot(
        place=3,
        attempts=(820, 801, 799, 814, 810),
        average=808,
        best=799,
        advanced=True,
    )
    text = format_round_result(
        "Spring in Moscow 2026",
        "https://cubingrf.org/competitions/x",
        "333",
        2,
        snap,
        language="ru",
    )
    # Heading comes first, competition and title follow, then place, then a
    # block holding attempts+stats, and advanced last.
    assert text.index("<h1>") < text.index("Spring in Moscow")
    assert text.index("Spring in Moscow") < text.index("раунд 2")
    assert text.index("раунд 2") < text.index("Место: 3")
    assert text.index("Место: 3") < text.index("Попытки:")
    assert text.index("вы прошли") > text.index("Среднее:")
    # The <h1> heading sits directly above the competition name with only a
    # line break (no blank line)…
    assert "<h1>🏁 Ваш результат в раунде</h1><a href=" in text
    # …while every later block is separated by exactly one blank line.
    assert "Spring in Moscow 2026</a><br/><br/>" in text
    assert "раунд 2<br/><br/>Место:" in text
    assert "Место: 3<br/><br/>Попытки:" in text
    assert "7.99<br/><br/>🏆 вы прошли" in text
    # …but attempts and the stats line share one block (single <br/>, no blank).
    assert "8.10<br/>Среднее:" in text


def test_format_round_result_edited_title():
    snap = RoundSnapshot(place=1, attempts=(500, 500, 500, 500, 500), average=500, best=500)
    text = format_round_result("Comp", None, "222", 1, snap, language="ru", edited=True)
    assert "был изменён" in text


def test_format_round_result_no_advancement_line_when_not_advanced():
    snap = RoundSnapshot(place=1, attempts=(500, 500, 500, 500, 500), average=500, best=500, advanced=False)
    text = format_round_result("Comp", None, "222", 1, snap, language="en")
    assert "advanced to the next round" not in text