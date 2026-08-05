"""Catalog of RF regions used on cubingrf.org.

Region names are stored in ``Competition.location`` as ``"<Region>, <City>"``,
so the region is always the part before the first comma. Moscow and Moscow
Oblast are considered one region ("Москва") per product decision, so both
location prefixes normalize to the same canonical key.
"""

# Canonical region keys (what the user selects and what is stored in user_regions).
REGIONS: list[tuple[str, str]] = [
    ("Москва", "Москва"),
    ("Санкт-Петербург", "Санкт-Петербург"),
    ("Новосибирская область", "Новосибирская область"),
    ("Приморский край", "Приморский край"),
    ("Красноярский край", "Красноярский край"),
    ("Краснодарский край", "Краснодарский край"),
    ("Свердловская область", "Свердловская область"),
    ("Нижегородская область", "Нижегородская область"),
    ("Республика Бурятия", "Республика Бурятия"),
    ("Ставропольский край", "Ставропольский край"),
    ("Пермский край", "Пермский край"),
    ("Республика Башкортостан", "Республика Башкортостан"),
    ("Ленинградская область", "Ленинградская область"),
    ("Мурманская область", "Мурманская область"),
    ("Республика Татарстан", "Республика Татарстан"),
    ("Тюменская область", "Тюменская область"),
    ("Саратовская область", "Саратовская область"),
    ("Самарская область", "Самарская область"),
    ("Ивановская область", "Ивановская область"),
    ("Республика Карелия", "Республика Карелия"),
    ("Алтайский край", "Алтайский край"),
    ("Челябинская область", "Челябинская область"),
    ("Республика Марий Эл", "Республика Марий Эл"),
    ("Омская область", "Омская область"),
    ("Республика Коми", "Республика Коми"),
]

REGION_LABELS: dict[str, str] = dict(REGIONS)

ALL_REGION_KEYS: list[str] = [key for key, _ in REGIONS]

_REGION_ORDER: dict[str, int] = {key: i for i, (key, _) in enumerate(REGIONS)}


def sort_region_keys(keys) -> list[str]:
    """Order region keys by the canonical catalog order (unknowns last)."""
    return sorted(keys, key=lambda k: _REGION_ORDER.get(k, len(_REGION_ORDER)))

# Location prefixes (from Competition.location) that map onto a canonical region.
# Moscow and Moscow Oblast are a single region "Москва".
_REGION_PREFIXES: dict[str, str] = {
    "Москва": "Москва",
    "Московская область": "Москва",
}

# Everything outside the known catalog is left as-is so unknown regions can be
# added later without breaking existing selections.
_REGION_PREFIXES.update({label: key for key, label in REGIONS})


def region_key_from_location(location: str | None) -> str | None:
    """Extract the canonical region key from a competition's location string.

    ``location`` looks like ``"Новосибирская область, Новосибирск"``. The part
    before the first comma is matched against the region catalog; unknown
    regions fall back to the raw prefix so nothing is lost.
    """
    if not location:
        return None
    prefix = location.split(",", 1)[0].strip()
    return _REGION_PREFIXES.get(prefix, prefix)