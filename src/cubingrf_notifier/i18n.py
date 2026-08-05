"""Minimal localization for the bot.

Texts live in ``locales/<language>.json`` files, one per supported language.
``language`` is a two-letter code ('ru', 'en', ...); unknown keys fall back to
the default language then to the key itself.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_LANGUAGE = "ru"

_LANGUAGES = ("ru", "en")
_LOCALES_DIR = Path(__file__).resolve().parent / "locales"


@lru_cache(maxsize=None)
def _load(language: str) -> dict[str, str]:
    path = _LOCALES_DIR / f"{language}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _available_keys() -> set[str]:
    """All translation keys defined across the bundled locales."""
    keys: set[str] = set()
    for lang in _LANGUAGES:
        keys.update(_load(lang).keys())
    return keys


def get_text(language: str, key: str, **kwargs: Any) -> str:
    """Translate ``key`` for ``language``, formatting ``{placeholders}``."""
    messages = _load(language) or {}
    template = messages.get(key)
    if template is None:
        template = _load(DEFAULT_LANGUAGE).get(key, key)
    return template.format(**kwargs)


def available_languages() -> tuple[str, ...]:
    return _LANGUAGES


def all_keys_present(language: str) -> bool:
    """True when every known translation key exists for this language."""
    return not (_available_keys() - set(_load(language).keys()))