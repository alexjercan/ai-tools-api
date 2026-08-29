from __future__ import annotations

import asyncio

from ai_tools_api.errors import ApiError


class ConcurrencyGate:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._active = 0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> None:
        async with self._lock:
            if self._active >= self._limit:
                raise ApiError("overloaded", 429)
            self._active += 1

    async def __aexit__(self, *_args: object) -> None:
        async with self._lock:
            self._active -= 1
