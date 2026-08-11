"""Pure, testable decision functions for round-result tracking.

These functions carry no I/O so they can be unit-tested in isolation; the
service in ``service.py`` orchestrates DB/HTTP/TG around them.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from .models import RoundResult, RoundSnapshot


def is_round_complete(results: list[RoundResult], roster_count: int) -> bool:
    """The completion heuristic.

    The site has no per-round "finished" flag, so a round is treated as
    finished when every rostered participant has a recorded result:

      1. there is a non-empty roster, and
      2. the number of recorded results equals the roster size, and
      3. every recorded result has at least one attempt.

    This is deliberately fail-safe: if a no-show never receives a result row
    the counts differ and we keep waiting rather than ever notifying early.
    The trade-off (a round may be reported slightly late if a rostered
    participant is genuinely left without a row) is accepted and documented.
    """
    if roster_count <= 0:
        return False
    if not results:
        return False
    if len(results) != roster_count:
        return False
    return all(bool(r.attempts) for r in results)


def snapshot_for(results: list[RoundResult], registrant_id: int) -> RoundSnapshot | None:
    """The user's own round snapshot, or None when they have no result row."""
    for r in results:
        if r.registrant_id == registrant_id:
            return RoundSnapshot(
                place=r.place,
                attempts=r.attempts,
                average=r.average,
                best=r.best,
                advanced=r.advanced,
            )
    return None


def hash_snapshot(snapshot: RoundSnapshot) -> str:
    """Fingerprint of a round snapshot; changes when the result is edited."""
    payload = {
        "place": snapshot.place,
        "attempts": list(snapshot.attempts),
        "average": snapshot.average,
        "best": snapshot.best,
        "advanced": snapshot.advanced,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def should_poll(
    *,
    now: datetime,
    completed: bool,
    completed_at: datetime | None,
    last_checked_at: datetime | None,
    base_interval: int = 60,
) -> bool:
    """Whether this (user, round) state should be fetched this tick.

    Unfinished rounds poll on every tick. Finished rounds back off as they
    age, so old results stop consuming bandwidth while still being re-checked
    occasionally to catch late edits. ``base_interval`` is the fast poll
    period in seconds.
    """
    if not completed:
        return True
    backoff = _backoff_seconds(now, completed_at, base_interval)
    if last_checked_at is None:
        return True
    age = (now - last_checked_at).total_seconds()
    return age >= backoff


def _backoff_seconds(now: datetime, completed_at: datetime | None, base: int) -> int:
    if completed_at is None:
        return base
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    age = (now - completed_at).total_seconds()
    if age < 3600:  # first hour: fast
        return base
    if age < 24 * 3600:  # first day: every 5 minutes
        return 300
    if age < 7 * 24 * 3600:  # first week: hourly
        return 3600
    return 6 * 3600  # after a week: every 6 hours
