from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cubingrf_notifier.competitions.availability import is_registration_available

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _comp(
    date=NOW + timedelta(days=5),
    end_date=None,
    registration_start_at=None,
    reg_status=None,
    cancelled_at=None,
):
    return SimpleNamespace(
        date=date,
        end_date=end_date,
        registration_start_at=registration_start_at,
        reg_status=reg_status,
        cancelled_at=cancelled_at,
    )


def test_open_registration_future_event():
    assert is_registration_available(_comp(reg_status="open"), NOW)


def test_scheduled_registration_future_event():
    assert is_registration_available(_comp(reg_status="scheduled"), NOW)


def test_unknown_status_with_future_registration_start():
    comp = _comp(registration_start_at=NOW + timedelta(days=1), reg_status=None)
    assert is_registration_available(comp, NOW)


def test_unknown_status_with_already_open_registration():
    comp = _comp(registration_start_at=NOW - timedelta(days=1), reg_status=None)
    assert is_registration_available(comp, NOW)


def test_unknown_status_without_dates_is_excluded():
    assert not is_registration_available(_comp(reg_status=None), NOW)


def test_started_competition_is_excluded():
    comp = _comp(date=NOW, reg_status="open")
    assert not is_registration_available(comp, NOW)


def test_finished_competition_is_excluded():
    comp = _comp(date=NOW - timedelta(days=3), end_date=NOW - timedelta(days=2), reg_status="open")
    assert not is_registration_available(comp, NOW)


def test_closed_registration_is_excluded():
    comp = _comp(date=NOW + timedelta(days=2), end_date=NOW + timedelta(days=3), reg_status="closed")
    assert not is_registration_available(comp, NOW)


def test_cancelled_competition_stays_visible():
    # Cancelled competitions remain on the page so the "Competition cancelled"
    # badge is shown; the cancelled state is rendered by the formatter.
    comp = _comp(date=NOW + timedelta(days=2), end_date=NOW + timedelta(days=3), reg_status="cancelled")
    assert is_registration_available(comp, NOW)


def test_cancelled_visible_immediately_after_detection():
    comp = _comp(reg_status="cancelled", cancelled_at=NOW)
    assert is_registration_available(comp, NOW)


def test_cancelled_visible_at_23h59_after_detection():
    comp = _comp(
        reg_status="cancelled",
        cancelled_at=NOW - timedelta(hours=23, minutes=59),
    )
    assert is_registration_available(comp, NOW)


def test_cancelled_hidden_after_24_hours():
    comp = _comp(reg_status="cancelled", cancelled_at=NOW - timedelta(hours=24))
    assert not is_registration_available(comp, NOW)


def test_cancelled_hidden_long_after_24_hours():
    comp = _comp(reg_status="cancelled", cancelled_at=NOW - timedelta(days=3))
    assert not is_registration_available(comp, NOW)


def test_cancelled_without_timestamp_stays_visible():
    # No cancelled_at yet (e.g. a legacy cancelled row before the service
    # stamps it) never vanishes abruptly.
    comp = _comp(reg_status="cancelled", cancelled_at=None)
    assert is_registration_available(comp, NOW)


def test_non_cancelled_unaffected_by_cancelled_at():
    # An open/scheduled competition ignores cancelled_at entirely.
    comp = _comp(reg_status="open", cancelled_at=NOW - timedelta(days=1))
    assert is_registration_available(comp, NOW)


def test_missing_date_is_excluded():
    comp = _comp(date=None, reg_status="open")
    assert not is_registration_available(comp, NOW)


def test_naive_datetimes_treated_as_utc():
    comp = _comp(reg_status="open")
    comp.date = datetime(2026, 8, 7, 12, 0)
    assert not is_registration_available(comp, NOW)


def test_default_now_is_used_without_arg():
    comp = _comp(reg_status="open", date=datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert is_registration_available(comp)