"""Catalog of RF regions used on cubingrf.org.

Region names are stored in ``Competition.location`` as ``"<Region>, <City>"``,
so the region is always the part before the first comma. Moscow and Moscow
Oblast are two distinct selectable regions; existing users who chose "Москва"
are migrated to have both (see the 0009 migration).
"""

# Canonical region keys (what the user selects and what is stored in
# user_regions). Each entry is (key, Russian label, English label).
REGIONS: list[tuple[str, str, str]] = [
    ("Москва", "Москва", "Moscow"),
    ("Московская область", "Московская область", "Moscow Oblast"),
    ("Санкт-Петербург", "Санкт-Петербург", "Saint Petersburg"),
    ("Новосибирская область", "Новосибирская область", "Novosibirsk Oblast"),
    ("Приморский край", "Приморский край", "Primorsky Krai"),
    ("Красноярский край", "Красноярский край", "Krasnoyarsk Krai"),
    ("Краснодарский край", "Краснодарский край", "Krasnodar Krai"),
    ("Свердловская область", "Свердловская область", "Sverdlovsk Oblast"),
    ("Нижегородская область", "Нижегородская область", "Nizhny Novgorod Oblast"),
    ("Республика Бурятия", "Республика Бурятия", "Republic of Buryatia"),
    ("Ставропольский край", "Ставропольский край", "Stavropol Krai"),
    ("Пермский край", "Пермский край", "Perm Krai"),
    ("Республика Башкортостан", "Республика Башкортостан", "Republic of Bashkortostan"),
    ("Ленинградская область", "Ленинградская область", "Leningrad Oblast"),
    ("Мурманская область", "Мурманская область", "Murmansk Oblast"),
    ("Республика Татарстан", "Республика Татарстан", "Republic of Tatarstan"),
    ("Тюменская область", "Тюменская область", "Tyumen Oblast"),
    ("Саратовская область", "Саратовская область", "Saratov Oblast"),
    ("Самарская область", "Самарская область", "Samara Oblast"),
    ("Ивановская область", "Ивановская область", "Ivanovo Oblast"),
    ("Республика Карелия", "Республика Карелия", "Republic of Karelia"),
    ("Алтайский край", "Алтайский край", "Altai Krai"),
    ("Челябинская область", "Челябинская область", "Chelyabinsk Oblast"),
    ("Республика Марий Эл", "Республика Марий Эл", "Mari El Republic"),
    ("Омская область", "Омская область", "Omsk Oblast"),
    ("Республика Коми", "Республика Коми", "Komi Republic"),
]

# Russian labels (key -> label). Keys are the Russian region names, so the
# Russian label equals the key itself.
REGION_LABELS: dict[str, str] = {key: ru for key, ru, _ in REGIONS}

# English labels (key -> label).
REGION_LABELS_EN: dict[str, str] = {key: en for key, _, en in REGIONS}

ALL_REGION_KEYS: list[str] = [key for key, _, _ in REGIONS]

_REGION_ORDER: dict[str, int] = {key: i for i, (key, _, _) in enumerate(REGIONS)}


def sort_region_keys(keys) -> list[str]:
    """Order region keys by the canonical catalog order (unknowns last)."""
    return sorted(keys, key=lambda k: _REGION_ORDER.get(k, len(_REGION_ORDER)))


def region_label(key: str, language: str = "ru") -> str:
    """Localized label for a region key (English for the en interface)."""
    if language == "en":
        return REGION_LABELS_EN.get(key, REGION_LABELS.get(key, key))
    return REGION_LABELS.get(key, key)

# Location prefixes (from Competition.location) that map onto a canonical region.
# Moscow and Moscow Oblast are two distinct regions.
_REGION_PREFIXES: dict[str, str] = {
    "Москва": "Москва",
    "Московская область": "Московская область",
}

# Everything outside the known catalog is left as-is so unknown regions can be
# added later without breaking existing selections.
_REGION_PREFIXES.update({ru: key for key, ru, _ in REGIONS})


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