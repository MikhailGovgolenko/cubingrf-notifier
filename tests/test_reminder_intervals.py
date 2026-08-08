from datetime import timedelta

from cubingrf_notifier.notifications.reminder_intervals import (
    REMINDER_INTERVALS,
    DEFAULT_REMINDER_INTERVAL,
    is_valid_reminder_interval,
    reminder_interval_label,
)
from cubingrf_notifier.notifications.reg_reminder import should_send_registration_reminder


def test_catalog_presets():
    assert REMINDER_INTERVALS == [10, 30, 60, 180, 720, 1440]
    assert DEFAULT_REMINDER_INTERVAL in REMINDER_INTERVALS


def test_is_valid_reminder_interval():
    for m in REMINDER_INTERVALS:
        assert is_valid_reminder_interval(m) is True
    assert is_valid_reminder_interval(0) is False
    assert is_valid_reminder_interval(90) is False
    assert is_valid_reminder_interval(7) is False


def test_reminder_interval_label_en():
    assert reminder_interval_label(10, "en") == "10 min"
    assert reminder_interval_label(30, "en") == "30 min"
    assert reminder_interval_label(60, "en") == "1 h"
    assert reminder_interval_label(180, "en") == "3 h"
    assert reminder_interval_label(720, "en") == "12 h"
    assert reminder_interval_label(1440, "en") == "1 days"


def test_reminder_interval_label_ru():
    assert reminder_interval_label(10, "ru") == "10 мин"
    assert reminder_interval_label(60, "ru") == "1 ч"
    assert reminder_interval_label(1440, "ru") == "1 дн"


def test_reminder_window_is_configurable():
    from datetime import datetime, timezone

    now = datetime(2026, 8, 16, 7, 0, tzinfo=timezone.utc)
    start_3h = now + timedelta(hours=3)  # 10:00
    start_12h = now + timedelta(hours=12)  # 19:00

    # Default 30-minute lead: target is 09:30 for start_3h → not yet now.
    assert should_send_registration_reminder(start_3h, now, 30) is False
    assert should_send_registration_reminder(start_12h, now, 30) is False
    # A 3-hour interval: target is 07:00 == now → due.
    assert should_send_registration_reminder(start_3h, now, 180) is True
    assert should_send_registration_reminder(start_12h, now, 180) is False
    # A 12-hour interval: target is 07:00 == now → due.
    assert should_send_registration_reminder(start_12h, now, 720) is True