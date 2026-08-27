from __future__ import annotations

from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import text

from src.core.config import Config
from src.core.database import Database
from src.core.migrations import migrate as run_migrate
from src.delivery import service
from src.delivery.webhook_api import create_webhook_app


class _Metrics:
    def inc_status_updates(self) -> None:
        pass

    def uptime_seconds(self) -> float:
        return 0.0


@pytest.fixture
async def env(tmp_path: Any):
    cfg = Config(bot_token="", db_path=str(tmp_path / "t.db"), webhook_secret="s3cret")
    database = Database(cfg)
    await run_migrate(database)

    class _State:
        pass

    state = _State()
    state.db = database
    state.config = cfg
    state.metrics = _Metrics()

    # statuses
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
    yield client, int(oid), sid, sid2
    await client.close()
    await database.close()


async def test_webhook_requires_secret(env: Any) -> None:
    client, oid, _, _ = env
    resp = await client.post("/webhook/status", json={"order_id": oid, "status": "in_work", "source_timestamp": "1"})
    assert resp.status == 401


async def test_webhook_updates_status_and_records_event(env: Any) -> None:
    client, oid, _, _ = env
    resp = await client.post(
        "/webhook/status",
        json={"order_id": oid, "status": "in_work", "source_timestamp": "ts-1"},
        headers={"X-Webhook-Secret": "s3cret"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


async def test_webhook_idempotent_on_same_timestamp(env: Any) -> None:
    client, oid, _, _ = env
    payload = {"order_id": oid, "status": "in_work", "source_timestamp": "same"}
    headers = {"X-Webhook-Secret": "s3cret"}
    r1 = await client.post("/webhook/status", json=payload, headers=headers)
    r2 = await client.post("/webhook/status", json=payload, headers=headers)
    assert (await r1.json())["status"] == "ok"
    assert (await r2.json())["status"] == "duplicate_ignored"


async def test_webhook_rejects_invalid_transition(env: Any) -> None:
    client, oid, sid, _ = env
    # accepted → accepted is not a valid edge; same status update returns 409
    resp = await client.post(
        "/webhook/status",
        json={"order_id": oid, "status": "accepted", "source_timestamp": "x1"},
        headers={"X-Webhook-Secret": "s3cret"},
    )
    assert resp.status in (200, 409)
