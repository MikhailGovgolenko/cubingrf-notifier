"""Decision helper: should a given user be notified about a competition.

Pure logic — no messaging, no storage, no I/O — so it can be unit-tested
with plain objects. User settings are read either from explicit arguments
(``user_region_keys`` / ``user_event_codes``) or from the ORM
relationships (``user.regions`` / ``user.events``).
"""
from typing import Iterable, List, Optional

from ..competitions.regions import ALL_REGION_KEYS, region_key_from_location
from ..competitions.disciplines import ALL_DISCIPLINE_CODES


def _covers_all(chosen: Iterable[str], catalog: Iterable[str]) -> bool:
    """Empty selection or the full catalog both mean "everything"."""
    selected = set(chosen)
    if not selected:
        return True
    return selected >= set(catalog)


def should_notify_user(
    user,
    competition,
    *,
    user_region_keys: Iterable[str] | None = None,
    user_event_codes: Iterable[str] | None = None,
) -> bool:
    """Decide whether ``user`` should be notified about ``competition``.

    ``user`` must expose ``notifications_enabled``; region keys and event
    codes are taken from the keyword arguments when given, otherwise from
    ``user.regions`` / ``user.events`` relationships.

    Empty selection and a full-catalog selection both behave as "all".
    """
    if not user.notifications_enabled:
        return False

    if user_region_keys is None:
        user_region_keys = _keys_from_relationship(user, "regions", "region_key")
    if user_event_codes is None:
        user_event_codes = _keys_from_relationship(user, "events", "event_code")

    if not _covers_all(user_region_keys, ALL_REGION_KEYS):
        comp_region = region_key_from_location(getattr(competition, "location", None))
        if comp_region not in set(user_region_keys):
            return False

    if not _covers_all(user_event_codes, ALL_DISCIPLINE_CODES):
        comp_codes = {code for code in (competition.disciplines or [])}
        if not (comp_codes & set(user_event_codes)):
            return False

    return True


def _keys_from_relationship(user, attr: str, field: str) -> List[str]:
    items = getattr(user, attr, None) or []
    return [getattr(item, field) for item in items]