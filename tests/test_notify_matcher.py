from types import SimpleNamespace

from cubingrf_notifier.notifications.matcher import should_notify_user
from cubingrf_notifier.competitions.regions import ALL_REGION_KEYS
from cubingrf_notifier.competitions.disciplines import ALL_DISCIPLINE_CODES


def _user(enabled=True, regions=None, disciplines=None):
    return SimpleNamespace(
        notifications_enabled=enabled,
        regions=[SimpleNamespace(region_key=r) for r in (regions or [])],
        disciplines=[SimpleNamespace(discipline_code=c) for c in (disciplines or [])],
    )


def _comp(location="Москва, Москва", disciplines=("333", "222")):
    return SimpleNamespace(location=location, disciplines=list(disciplines))


def test_disabled_notifications_never_notify():
    user = _user(enabled=False, regions=["Москва"], disciplines=["333"])
    assert should_notify_user(user, _comp()) is False


def test_region_matches_notifies():
    user = _user(regions=["Москва"], disciplines=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва")) is True


def test_region_matches_via_moscow_oblong_alias():
    user = _user(regions=["Москва"])
    assert should_notify_user(user, _comp(location="Московская область, Щёлково")) is True


def test_region_does_not_match():
    user = _user(regions=["Омская область"])
    assert should_notify_user(user, _comp(location="Москва, Москва")) is False


def test_discipline_matches_notifies():
    user = _user(regions=["Москва"], disciplines=["444"])
    assert should_notify_user(user, _comp(disciplines=["333", "444"])) is True


def test_discipline_does_not_match():
    user = _user(regions=["Москва"], disciplines=["444"])
    assert should_notify_user(user, _comp(disciplines=["333", "222"])) is False


def test_region_and_discipline_both_match():
    user = _user(regions=["Москва"], disciplines=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is True


def test_region_matches_but_discipline_does_not():
    user = _user(regions=["Москва"], disciplines=["444"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is False


def test_region_does_not_match_but_discipline_does():
    user = _user(regions=["Омская область"], disciplines=["333"])
    assert should_notify_user(user, _comp(location="Москва, Москва", disciplines=["333"])) is False


def test_all_regions_matches_anything():
    user = _user(regions=list(ALL_REGION_KEYS), disciplines=["333"])
    assert should_notify_user(user, _comp(location="Омская область, Омск")) is True


def test_all_disciplines_matches_anything():
    user = _user(regions=["Москва"], disciplines=list(ALL_DISCIPLINE_CODES))
    assert should_notify_user(user, _comp(disciplines=["333bf"])) is True


def test_empty_settings_means_all():
    user = _user()
    assert should_notify_user(user, _comp(location="Какой-то край, Город", disciplines=["clock"])) is True


def test_explicit_region_keys_argument_wins():
    user = _user(regions=["Москва"], disciplines=["333"])
    assert should_notify_user(
        user,
        _comp(location="Омская область, Омск"),
        user_region_keys=["Омская область"],
    ) is True
