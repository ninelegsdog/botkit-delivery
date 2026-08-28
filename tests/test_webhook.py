"""Webhook endpoint tests for the delivery status webhook (in-process aiohttp).

botkit-delivery exposes its webhook via a plain aiohttp app
(`src/delivery/webhook_api.py`) rather than aiogram's SimpleRequestHandler.
The endpoint enforces the `X-Webhook-Secret` header and returns 401 on a
missing/wrong secret, 2xx on a valid status update, and 4xx/5xx on malformed
bodies.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import text

from src.core.config import Config
from src.core.database import Database
from src.core.migrations import migrate as run_migrate
from src.delivery import service
from src.delivery.webhook_api import create_webhook_app

SECRET = "local-test-secret"


class _Metrics:
    def inc_status_updates(self) -> None: ...

    def uptime_seconds(self) -> float:
        return 0.0


@pytest.fixture
async def webhook_client(tmp_path: Any) -> Any:
    cfg = Config(bot_token="", db_path=str(tmp_path / "t.db"), webhook_secret=SECRET)
    database = Database(cfg)
    await run_migrate(database)

    state = SimpleNamespace(db=database, config=cfg, metrics=_Metrics())

    async with database.transaction() as session:
        await session.execute(text("INSERT INTO statuses (name) VALUES ('accepted'), ('in_work')"))
        row = await session.execute(text("SELECT id FROM statuses WHERE name='accepted'"))
        sid = int(row.scalar_one())
        row = await session.execute(text("SELECT id FROM statuses WHERE name='in_work'"))
        sid2 = int(row.scalar_one())
        await session.execute(
            text("INSERT INTO status_transitions (from_status_id, to_status_id) VALUES (:a, :b)"),
            {"a": sid, "b": sid2},
        )
    oid = await service.create_order(database, number="ORD-1", client_label="Иван", title="Костюм", status_id=sid)

    app = create_webhook_app(state)  # type: ignore[arg-type]
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client, int(oid)
    await client.close()
    await database.close()


@pytest.mark.no_req
@pytest.mark.webhook
async def test_webhook_accepts_valid_secret(webhook_client: TestClient) -> None:
    client, oid = webhook_client
    resp = await client.post(
        "/webhook/status",
        json={"order_id": oid, "status": "in_work", "source_timestamp": "ts-1"},
        headers={"X-Webhook-Secret": SECRET},
    )
    assert resp.status in (200, 202)


@pytest.mark.no_req
@pytest.mark.webhook
async def test_webhook_rejects_wrong_secret(webhook_client: TestClient) -> None:
    client, oid = webhook_client
    resp = await client.post(
        "/webhook/status",
        json={"order_id": oid, "status": "in_work", "source_timestamp": "ts-1"},
        headers={"X-Webhook-Secret": "wrong"},
    )
    assert resp.status in (401, 403)


@pytest.mark.no_req
@pytest.mark.webhook
async def test_webhook_rejects_missing_secret(webhook_client: TestClient) -> None:
    client, oid = webhook_client
    resp = await client.post(
        "/webhook/status",
        json={"order_id": oid, "status": "in_work", "source_timestamp": "ts-1"},
    )
    assert resp.status in (401, 403)


@pytest.mark.no_req
@pytest.mark.webhook
async def test_webhook_rejects_bad_json(webhook_client: TestClient) -> None:
    client, _ = webhook_client
    resp = await client.post(
        "/webhook/status",
        data=b"not-json",
        headers={
            "X-Webhook-Secret": SECRET,
            "Content-Type": "application/json",
        },
    )
    assert resp.status in (400, 415, 500)
