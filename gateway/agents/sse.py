"""Shared SSE consumption for the upstream agent streams.

All three agents speak `text/event-stream` with one JSON object per
`data: ` line (same wire format the Next.js proxies forward verbatim).
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

# Agent 3 XOSC generation runs up to 10 min; no read timeout, generous total.
STREAM_TIMEOUT = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0)


async def stream_json_events(url: str, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """POST `payload` to `url` and yield each `data: {...}` event as a dict."""
    async with httpx.AsyncClient(timeout=STREAM_TIMEOUT) as client:
        async with client.stream(
            "POST",
            url,
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue  # keepalives / partial lines
