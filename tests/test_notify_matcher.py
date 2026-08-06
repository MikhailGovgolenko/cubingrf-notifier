from types import SimpleNamespace

from cubingrf_notifier.notifications.matcher import (
    should_notify_user,
    KIND_ANNOUNCEMENT,
    KIND_REG_SOON,
)
from cubingrf_notifier.competitions.regions import ALL_REGION_KEYS
from cubingrf_notifier.competitions.disciplines import ALL_DISCIPLINE_CODES


def _user(
    enabled=True,
    regions=None,
    events=None,
    announcements=True,
    registrations=True,
):
    return SimpleNamespace(
        notifications_enabled=enabled,
        announcements_enabled=announcements,
        registration_notifications_enabled=registrations,
        regions=[SimpleNamespace(region_key=r) for r in (regions or [])],
        events=[SimpleNamespace(event_code=c) for c in (events or [])],
    )


def _comp(location="Москва, Москва", disciplines=("333", "222")):
    return SimpleNamespace(location=location, disciplines=list(disciplines))


def test_disabled_notifications_never_notify():
    user = _user(enabled=False, regions=["Москва"], events=["333"])
    assert should_notify_user(user, _comp()) is False


def test_region_matches_notifies():
    user = _user(regions=["Москва"], events=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва")) is True


def test_region_moscow_oblong_is_distinct():
    user = _user(regions=["Москва"])
    assert should_notify_user(user, _comp(location="Московская область, Щёлково")) is False
    user = _user(regions=["Московская область"])
    assert should_notify_user(user, _comp(location="Московская область, Щёлково")) is True


def test_region_does_not_match():
    user = _user(regions=["Омская область"])
    assert should_notify_user(user, _comp(location="Москва, Москва")) is False


def test_discipline_matches_notifies():
    user = _user(regions=["Москва"], events=["444"])
    assert should_notify_user(user, _comp(disciplines=["333", "444"])) is True


def test_discipline_does_not_match():
    user = _user(regions=["Москва"], events=["444"])
    assert should_notify_user(user, _comp(disciplines=["333", "222"])) is False


def test_region_and_discipline_both_match():
    user = _user(regions=["Москва"], events=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is True


def test_region_matches_but_discipline_does_not():
    user = _user(regions=["Москва"], events=["444"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is False


def test_region_does_not_match_but_discipline_does():
    user = _user(regions=["Омская область"], events=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is False


def test_all_regions_matches_anything():
    user = _user(regions=list(ALL_REGION_KEYS), events=["333"])
    assert should_notify_user(user, _comp(location="Омская область, Омск")) is True


def test_all_disciplines_matches_anything():
    user = _user(regions=["Москва"], events=list(ALL_DISCIPLINE_CODES))
    assert should_notify_user(user, _comp(disciplines=["333bf"])) is True


def test_empty_settings_means_all():
    user = _user()
    assert should_notify_user(user, _comp(location="Какой-то край, Город", disciplines=["clock"])) is True


def test_explicit_region_keys_argument_wins():
    user = _user(regions=["Москва"], events=["333"])
    assert should_notify_user(
        user,
        _comp(location="Омская область, Омск"),
        user_region_keys=["Омская область"],
    ) is True


# ---------- per-type notification switches ----------

def test_announcements_off_blocks_announcement_kind():
    user = _user(announcements=False)
    assert should_notify_user(user, _comp(), kind=KIND_ANNOUNCEMENT) is False


def test_announcements_off_does_not_block_registration_kind():
    user = _user(announcements=False)
    assert should_notify_user(user, _comp(), kind=KIND_REG_SOON) is True


def test_registrations_off_blocks_registration_kind():
    user = _user(registrations=False)
    assert should_notify_user(user, _comp(), kind=KIND_REG_SOON) is False


def test_registrations_off_does_not_block_announcement_kind():
    user = _user(registrations=False)
    assert should_notify_user(user, _comp(), kind=KIND_ANNOUNCEMENT) is True


def test_default_kind_is_announcement():
    user = _user(announcements=False)
    assert should_notify_user(user, _comp()) is False
    assert should_notify_user(user, _comp(), kind="new") is False


def test_both_off_blocks_both_kinds():
    user = _user(announcements=False, registrations=False)
    assert should_notify_user(user, _comp(), kind=KIND_ANNOUNCEMENT) is False
    assert should_notify_user(user, _comp(), kind=KIND_REG_SOON) is False
