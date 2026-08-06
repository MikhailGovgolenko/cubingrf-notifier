"""Helpers for sending Telegram Rich Messages.

Rich Messages (Bot API 10.1+, ``sendRichMessage``) use a richer HTML than the
legacy ``parse_mode=HTML``: headings ``<h1>``-``<h6>``, ``<hr/>``, ``<br>``,
lists, tables, block quotations, media and more. Unlike plain ``parse_mode``,
line breaks are only produced by ``<br/>`` (a literal ``\\n`` is collapsed), so
all rendered text must use ``<br/>`` for breaks.
"""
from aiogram.types import InputRichMessage


def rich_html(html: str) -> InputRichMessage:
    """Wrap already-rendered Rich Message HTML into an ``InputRichMessage``."""
    return InputRichMessage(html=html)