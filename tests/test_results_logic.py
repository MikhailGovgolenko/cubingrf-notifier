import pytest
from datetime import datetime, timedelta, timezone

from cubingrf_notifier.results.models import RoundResult, RoundSnapshot
from cubingrf_notifier.results.logic import (
    is_round_complete,
    snapshot_for,
    hash_snapshot,
    should_poll,
)


def _res(rid, place=1, attempts=(5, 5, 5, 5, 5), advanced=False, average=5, best=5):
    return RoundResult(
        registrant_id=rid,
        place=place,
        attempts=attempts,
        average=average,
        best=best,
        advanced=advanced,
    )


# --- is_round_complete ---

def test_complete_round_when_all_rostered_have_results():
    results = [_res(1), _res(2), _res(3)]
    assert is_round_complete(results, roster_count=3) is True


def test_incomplete_when_fewer_results_than_roster():
    results = [_res(1), _res(2)]
    assert is_round_complete(results, roster_count=3) is False


def test_incomplete_when_no_roster():
    assert is_round_complete([_res(1)], roster_count=0) is False


def test_incomplete_when_no_results():
    assert is_round_complete([], roster_count=3) is False


def test_incomplete_when_rostered_participant_has_no_attempts():
    results = [_res(1, attempts=(5, 5, 5, 5, 5)), _res(2, attempts=())]
    assert is_round_complete(results, roster_count=2) is False


# --- snapshot_for ---

def test_snapshot_for_finds_user():
    results = [_res(1), _res(2, place=2, attempts=(9, 9, 9, 9, 9), average=9, best=9, advanced=True)]
    snap = snapshot_for(results, 2)
    assert snap is not None
    assert snap.place == 2
    assert snap.attempts == (9, 9, 9, 9, 9)
    assert snap.average == 9
    assert snap.best == 9
    assert snap.advanced is True


def test_snapshot_for_returns_none_when_user_absent():
    results = [_res(1)]
    assert snapshot_for(results, 999) is None


# --- hash_snapshot ---

def test_hash_is_stable_for_equal_snapshots():
    a = RoundSnapshot(place=1, attempts=(5, 5, 5, 5, 5), average=5, best=5, advanced=True)
    b = RoundSnapshot(place=1, attempts=(5, 5, 5, 5, 5), average=5, best=5, advanced=True)
    assert hash_snapshot(a) == hash_snapshot(b)


def test_hash_changes_when_result_edited():
    a = RoundSnapshot(place=1, attempts=(5, 5, 5, 5, 5), average=5, best=5, advanced=True)
    b = RoundSnapshot(place=1, attempts=(5, 5, 5, 5, 4), average=5, best=5, advanced=True)
    assert hash_snapshot(a) != hash_snapshot(b)


# --- should_poll ---

def test_unfinished_round_always_polls():
    now = datetime.now(timezone.utc)
    assert should_poll(now=now, completed=False, completed_at=None, last_checked_at=None) is True


def test_newly_completed_round_polls_frequently():
    now = datetime.now(timezone.utc)
    completed_at = now - timedelta(seconds=30)
    long_ago = now - timedelta(seconds=120)
    assert should_poll(now=now, completed=True, completed_at=completed_at, last_checked_at=long_ago, base_interval=60) is True
    recent = now - timedelta(seconds=10)
    assert should_poll(now=now, completed=True, completed_at=completed_at, last_checked_at=recent, base_interval=60) is False


def test_old_completed_round_backs_off():
    now = datetime.now(timezone.utc)
    completed_at = now - timedelta(days=3)
    last = now - timedelta(seconds=100)
    # >1 day old -> 3600s backoff; only 100s since last poll -> skip.
    assert should_poll(now=now, completed=True, completed_at=completed_at, last_checked_at=last, base_interval=60) is False
    last_old = now - timedelta(seconds=4000)
    assert should_poll(now=now, completed=True, completed_at=completed_at, last_checked_at=last_old, base_interval=60) is True