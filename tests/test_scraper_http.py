"""Regression tests for the bounded, streaming HTTP fetch used by scrapers.

External HTML/JSON is untrusted input: an oversized response must be discarded
before it is buffered (DoS guard), HTTP errors must yield None, and a normal
small body must be returned as text.
"""
import httpx

from cubingrf_notifier.scrapers.http import fetch_text


async def test_fetch_text_returns_small_body():
    async def handler(request):
        return httpx.Response(200, text="<html>ok</html>")

    transport = httpx.MockTransport(handler)
    result = await fetch_text("https://example.invalid/", transport=transport)
    assert result == "<html>ok</html>"


async def test_fetch_text_discards_oversized_body():
    async def handler(request):
        return httpx.Response(200, content=b"x" * 1000)

    transport = httpx.MockTransport(handler)
    result = await fetch_text("https://example.invalid/", transport=transport, max_bytes=100)
    assert result is None


async def test_fetch_text_returns_none_on_http_error():
    async def handler(request):
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    result = await fetch_text("https://example.invalid/", transport=transport)
    assert result is None


async def test_fetch_text_returns_none_on_connection_error():
    async def handler(request):
        raise httpx.ConnectError("refused")

    transport = httpx.MockTransport(handler)
    result = await fetch_text("https://example.invalid/", transport=transport)
    assert result is None