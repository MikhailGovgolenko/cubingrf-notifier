"""Shared, bounded HTTP fetching for the scrapers.

External HTML is treated as untrusted input: responses are read in a bounded
stream so an oversized or misbehaving server cannot force us to buffer an
unbounded body in memory (DoS guard).
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Cap on a single page/response we are willing to parse. Competition, results
# and roster pages are small; a larger body indicates a misbehaving server and
# must be discarded before it is buffered.
MAX_BODY_BYTES = 5 * 1024 * 1024

DEFAULT_USER_AGENT = "cubingrf-notifier/0.1"


async def fetch_text(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = 15.0,
    max_bytes: int = MAX_BODY_BYTES,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Optional[str]:
    """Fetch ``url`` and return its text, bounded by ``max_bytes``.

    The body is streamed so an oversized response is detected and discarded
    before it is fully buffered. Returns ``None`` on any HTTP error or when the
    body exceeds ``max_bytes``; never raises. ``transport`` is injectable for
    tests.
    """
    headers = {"User-Agent": user_agent}
    client_kwargs: dict = {"timeout": timeout, "follow_redirects": True}
    if transport is not None:
        client_kwargs["transport"] = transport
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        logger.warning(
                            "Response from %s exceeded %d bytes; discarding",
                            url,
                            max_bytes,
                        )
                        return None
                    chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None