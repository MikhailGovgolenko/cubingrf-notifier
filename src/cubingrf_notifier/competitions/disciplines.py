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

ALL_DISCIPLINE_CODES: list[str] = [code for code, _ in DISCIPLINES]


def discipline_label(code: str) -> str:
    """Human-readable label for a discipline code; falls back to the code."""
    return DISCIPLINE_LABELS.get(code, code)