from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis_url: str, min_interval: float = 2.0) -> None:
        super().__init__()
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._min_interval = min_interval
        self._local_cache: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else 0
            now = time.time()

            # Check local cache first (fast path)
            last = self._local_cache.get(user_id, 0.0)
            if now - last < self._min_interval:
                # Double-check with Redis
                try:
                    redis_last = await self._redis.get(f"throttle:{user_id}")
                    if redis_last and now - float(redis_last) < self._min_interval:
                        return None
                except Exception:
                    pass  # Fallback to local cache on Redis errors

            # Update both local and Redis
            self._local_cache[user_id] = now
            try:
                await self._redis.set(f"throttle:{user_id}", str(now), ex=int(self._min_interval * 2))
            except Exception:
                pass  # Don't fail on Redis errors
        return await handler(event, data)
