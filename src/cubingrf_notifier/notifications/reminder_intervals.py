"""Chosen "how far in advance" presets for registration reminders.

The value stored on the user (``User.reg_reminder_interval``) is a number of
minutes. The catalog below is what the settings menu offers and what the
"interval distribution" statistics group by.
"""
from ..i18n import get_text

# Minutes before registration opens at which a reminder is delivered.
REMINDER_INTERVALS: list[int] = [10, 30, 60, 180, 720, 1440]

DEFAULT_REMINDER_INTERVAL = 30

_REMINDER_INTERVAL_SET: set[int] = set(REMINDER_INTERVALS)


def is_valid_reminder_interval(minutes: int) -> bool:
    return minutes in _REMINDER_INTERVAL_SET


def reminder_interval_label(minutes: int, language: str = "en") -> str:
    """Human label for a reminder interval in minutes."""
    if minutes % 1440 == 0:
        days = minutes // 1440
        return get_text(language, "intervals.label_days", count=days)
    if minutes % 60 == 0:
        hours = minutes // 60
        return get_text(language, "intervals.label_hours", count=hours)
    return get_text(language, "intervals.label_minutes", count=minutes)