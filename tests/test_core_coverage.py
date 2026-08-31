from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core import auth, payments, sentry, storage
from src.core.config import Config
from src.core.metrics import Metrics, UpdatesMiddleware


@pytest.mark.asyncio
async def test_payment_provider():
    prov = payments.MockPaymentProvider()
    pid = await prov.create_payment(title="t", description="d", payload="p", amount=100)
    assert pid == "mock_payment_123"
    assert await prov.check_payment("x") is True
    assert payments.PaymentProvider.__abstractmethods__


def test_sentry_no_dsn():
    sentry.init_sentry("")
    sentry.init_sentry(None)


@pytest.mark.asyncio
async def test_auth_middleware():
    db = MagicMock()
    mw = auth.AuthMiddleware(db)
    sent = {}

    async def handler(event, data):
        sent.update(data)
        return "ok"

    assert await mw.__call__(handler, MagicMock(), {}) == "ok"
    assert sent.get("db") is db


@pytest.mark.asyncio
async def test_metrics_counter():
    m = Metrics()
    m.inc_messages()
    m.inc_status_updates()
    m.inc_notifications_sent()
    m.inc_errors()
    assert m.messages_processed == 1
    assert m.status_updates == 1
    assert m.notifications_sent == 1
    assert m.errors == 1
    assert m.uptime_seconds() >= 0


@pytest.mark.asyncio
async def test_updates_middleware():
    mw = UpdatesMiddleware()

    async def handler(event, data):
        return "done"

    assert await mw.__call__(handler, MagicMock(), {}) == "done"


@pytest.mark.asyncio
async def test_storage(db):
    s = storage.Storage(db)
    assert await s.get_setting("missing") is None
    await s.set_setting("k", "v")
    assert await s.get_setting("k") == "v"


def test_config_from_env_admin_ids(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1, ,x,2")
    cfg = Config.from_env()
    assert cfg.admin_ids == [1, 2]
