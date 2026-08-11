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


def test_format_round_result_edited_title():
    snap = RoundSnapshot(place=1, attempts=(500, 500, 500, 500, 500), average=500, best=500)
    text = format_round_result("Comp", None, "222", 1, snap, language="ru", edited=True)
    assert "был изменён" in text


def test_format_round_result_no_advancement_line_when_not_advanced():
    snap = RoundSnapshot(place=1, attempts=(500, 500, 500, 500, 500), average=500, best=500, advanced=False)
    text = format_round_result("Comp", None, "222", 1, snap, language="en")
    assert "advanced to the next round" not in text