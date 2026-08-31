from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message, User
from aiohttp.test_utils import TestClient, TestServer

from src.core import webhook
from src.core.metrics import Metrics
from src.core.throttling import ThrottlingMiddleware


def test_message(user_id: int = 42) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="T"),
        text="hello",
    )


@pytest.mark.asyncio
async def test_throttled_returns_none():
    mw = ThrottlingMiddleware("redis://localhost:6379/0", min_interval=100.0)
    mw._local_cache = {42: time.time()}
    mw._redis.get = AsyncMock(return_value=str(time.time()))

    async def handler(event, data):
        return "ok"

    assert await mw.__call__(handler, test_message(42), {}) is None


@pytest.mark.asyncio
async def test_throttled_redis_error_falls_back():
    mw = ThrottlingMiddleware("redis://localhost:6379/0", min_interval=100.0)
    mw._local_cache = {42: time.time()}
    mw._redis.get = AsyncMock(side_effect=RuntimeError("redis down"))
    mw._redis.set = AsyncMock()

    async def handler(event, data):
        return "ok"

    await mw.__call__(handler, test_message(42), {})
    assert mw._local_cache.get(42) is not None


@pytest.mark.asyncio
async def test_webhook_health():
    state = MagicMock()
    db = MagicMock()
    db.session.return_value.__aenter__ = AsyncMock()
    db.session.return_value.__aexit__ = AsyncMock(return_value=False)
    state.db = db
    state.metrics = Metrics()
    client = TestClient(TestServer(webhook.create_app(state)))
    await client.start_server()
    try:
        ok = await client.get("/health")
        assert ok.status == 200
    finally:
        await client.close()

    state2 = MagicMock()
    err_db = MagicMock()
    err_db.session.side_effect = Exception("boom")
    state2.db = err_db
    state2.metrics = Metrics()
    client2 = TestClient(TestServer(webhook.create_app(state2)))
    await client2.start_server()
    try:
        bad = await client2.get("/health")
        assert bad.status == 500
    finally:
        await client2.close()


@pytest.mark.asyncio
async def test_webhook_metrics():
    state = MagicMock()
    state.metrics = Metrics()
    client = TestClient(TestServer(webhook.create_app(state)))
    await client.start_server()
    try:
        resp = await client.get("/metrics")
        assert resp.status == 200
        body = await resp.json()
        assert "messages" in body
    finally:
        await client.close()
