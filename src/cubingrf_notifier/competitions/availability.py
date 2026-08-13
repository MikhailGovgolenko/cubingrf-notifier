"""Decision helper: can a user still register for a competition.

Used by the ``/competitions`` list to show only competitions the user could
actually register for. Real dates are the primary source of truth
(``date`` / ``end_date`` / ``registration_start_at``); ``reg_status`` is used
as a supplementary signal and never as the sole condition.
"""
from datetime import datetime, timezone

# Registration statuses that independently confirm availability.
_OPEN = "open"
_SCHEDULED = "scheduled"
_CLOSED = "closed"
_CANCELLED = "cancelled"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_registration_available(
    comp,
    now: datetime | None = None,
) -> bool:
    """Whether ``comp`` should appear in the upcoming-competitions list.

    A competition is shown only when there is enough information to conclude
    that registration is or will be open *and* the competition itself has not
    started yet:

    * event finished (``end_date`` in the past) → excluded;
    * event already started (``date`` today or earlier) → excluded;
    * missing event start date → excluded (not enough information);
    * ``reg_status == 'closed'`` → excluded;
    * ``reg_status == 'cancelled'`` → kept visible so the page can show the
      "Competition cancelled" badge (the cancelled state is rendered by the
      formatter, not by this helper);
    * ``reg_status`` open/scheduled and event not started → shown;
    * unknown ``reg_status``: shown only when ``registration_start_at`` is
      known (a past/future opening means registration is or will be open, and
      the event is still ahead).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now = _as_utc(now) or now

    end = _as_utc(getattr(comp, "end_date", None))
    start = _as_utc(getattr(comp, "date", None))
    reg_start = _as_utc(getattr(comp, "registration_start_at", None))
    reg_status = getattr(comp, "reg_status", None)

    if end is not None and end < now:
        return False
    if start is None:
        return False
    if start <= now:
        return False

    if reg_status == _CLOSED:
        return False
    if reg_status == _CANCELLED:
        # Kept visible: the competitions page shows the cancellation badge.
        return True
    if reg_status in (_OPEN, _SCHEDULED):
        return True
    if reg_start is None:
        return False
    return True