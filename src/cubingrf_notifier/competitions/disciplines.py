"""Catalog of WCA discipline codes used by cubingrf.org (event-XXX classes)."""

DISCIPLINES: list[tuple[str, str]] = [
    ("333", "3x3x3"),
    ("222", "2x2x2"),
    ("444", "4x4x4"),
    ("555", "5x5x5"),
    ("666", "6x6x6"),
    ("777", "7x7x7"),
    ("333bf", "3x3 Blindfolded"),
    ("333fm", "3x3 Fewest Moves"),
    ("333oh", "3x3 One-Handed"),
    ("clock", "Clock"),
    ("minx", "Megaminx"),
    ("pyram", "Pyraminx"),
    ("skewb", "Skewb"),
    ("sq1", "Square-1"),
    ("444bf", "4x4 Blindfolded"),
    ("555bf", "5x5 Blindfolded"),
    ("333mbf", "3x3 Multi-Blind"),
]

DISCIPLINE_LABELS: dict[str, str] = dict(DISCIPLINES)

# Compact labels for the competition card's discipline line.
DISCIPLINE_SHORT_LABELS: dict[str, str] = {
    "333": "3x3",
    "222": "2x2",
    "444": "4x4",
    "555": "5x5",
    "666": "6x6",
    "777": "7x7",
    "333bf": "3BLD",
    "333fm": "FMC",
    "333oh": "OH",
    "clock": "Clock",
    "minx": "Megaminx",
    "pyram": "Pyraminx",
    "skewb": "Skewb",
    "sq1": "Square-1",
    "444bf": "4BLD",
    "555bf": "5BLD",
    "333mbf": "MBLD",
}

ALL_DISCIPLINE_CODES: list[str] = [code for code, _ in DISCIPLINES]

_DISCIPLINE_ORDER: dict[str, int] = {code: i for i, (code, _) in enumerate(DISCIPLINES)}


def sort_discipline_codes(codes) -> list[str]:
    """Order discipline codes by the canonical catalog order.

    Unknown codes (not in the catalog) are pushed to the end so they never
    break the ordering. This is the single source of ordering for both the
    competition card and the selection keyboard.
    """
    return sorted(codes, key=lambda c: _DISCIPLINE_ORDER.get(c, len(_DISCIPLINE_ORDER)))


def discipline_label(code: str) -> str:
    """Human-readable label for a discipline code; falls back to the code."""
    return DISCIPLINE_LABELS.get(code, code)


def discipline_short_label(code: str) -> str:
    """Compact label for a discipline code; falls back to the full label."""
    return DISCIPLINE_SHORT_LABELS.get(code, discipline_label(code))