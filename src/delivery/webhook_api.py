from __future__ import annotations

import logging

from aiohttp import web
from sqlalchemy import text

from src.core.bot_factory import AppState
from src.delivery import service

logger = logging.getLogger(__name__)


async def _is_duplicate(state: AppState, order_id: int, status_id: int, ts: str) -> bool:
    async with state.db.session() as session:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM webhook_events "
                "WHERE order_id = :oid AND status_id = :sid AND source_timestamp = :ts"
            ),
            {"oid": order_id, "sid": status_id, "ts": ts},
        )
        return int(result.scalar_one()) > 0


async def _record_event(state: AppState, order_id: int, status_id: int, ts: str) -> None:
    async with state.db.transaction() as session:
        await session.execute(
            text("INSERT INTO webhook_events (order_id, status_id, source_timestamp) VALUES (:oid, :sid, :ts)"),
            {"oid": order_id, "sid": status_id, "ts": ts},
        )


async def webhook_status(request: web.Request) -> web.Response:
    state: AppState = request.app["state"]
    secret = request.headers.get("X-Webhook-Secret", "")
    if not state.config.webhook_secret or secret != state.config.webhook_secret:
        return web.json_response({"error": "unauthorized"}, status=401)

    try:
        body = await request.json()
        order_id = int(body["order_id"])
        status_name = str(body["status"])
        ts = str(body.get("source_timestamp", ""))
    except (KeyError, ValueError, TypeError):
        return web.json_response({"error": "bad payload"}, status=400)
    if not ts:
        return web.json_response({"error": "source_timestamp required"}, status=400)

    statuses = {s["name"]: int(s["id"]) for s in await service.get_statuses(state.db)}
    status_id = statuses.get(status_name)
    if status_id is None:
        return web.json_response({"error": "unknown status"}, status=400)

    if await _is_duplicate(state, order_id, status_id, ts):
        return web.json_response({"status": "duplicate_ignored"})

    order = await service.get_order(state.db, order_id)
    if order is None:
        return web.json_response({"error": "order not found"}, status=404)

    ok = await service.update_order_status(
        state.db,
        order_id,
        status_id,
        changed_by=None,
        comment=f"webhook: {status_name}",
    )
    if not ok:
        return web.json_response({"error": "invalid transition"}, status=409)

    await _record_event(state, order_id, status_id, ts)
    state.metrics.inc_status_updates()
    return web.json_response({"status": "ok"})


def create_webhook_app(state: AppState) -> web.Application:
    app = web.Application()
    app["state"] = state
    app.router.add_post("/webhook/status", webhook_status)
    return app
