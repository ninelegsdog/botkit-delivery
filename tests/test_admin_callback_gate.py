"""Admin callbacks must be gated, and the gate must accept password-authorised admins.

Two gaps were reachable from Telegram:

1. The mutation callbacks (``close:``, ``close_yes:``, ``close_no``, ``next:``,
   ``order_confirm``, ``order_cancel``, ``os:``) carried no ``is_admin`` check at
   all, so any user who sent the callback_data could advance or close an order.
2. ``is_admin`` read only ``config.admin_ids``, so a user who proved the admin
   password via ``/admin`` was refused by the very panels the gate opened for them.
   These tests call the handlers the router actually registered, so the guard is
   exercised rather than assumed.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.admin.handlers import create_admin_router
from src.core.config import Config


def _app_state(admin_ids: list[int]) -> Any:
    cfg = Config(
        bot_token="123456789:AAfake",
        admin_password="secret",
        admin_ids=admin_ids,
        redis_url="redis://localhost:6379/0",
    )
    return SimpleNamespace(config=cfg, db=MagicMock())


def _handler(router: Any, name: str) -> Any:
    for h in router.callback_query.handlers:
        if getattr(h.callback, "__name__", None) == name:
            return h.callback
    raise AssertionError(f"callback handler {name!r} not found")


def _message_handler(router: Any, name: str) -> Any:
    for h in router.message.handlers:
        if getattr(h.callback, "__name__", None) == name:
            return h.callback
    raise AssertionError(f"message handler {name!r} not found")


def _callback(uid: int, data: str) -> Any:
    cq = MagicMock()
    cq.data = data
    cq.from_user = MagicMock()
    cq.from_user.id = uid
    cq.answer = AsyncMock()
    cq.message = MagicMock()
    cq.message.edit_text = AsyncMock()
    cq.message.answer = AsyncMock()
    return cq


def _message(uid: int, text: str) -> Any:
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = uid
    msg.text = text
    msg.answer = AsyncMock()
    return msg


def _fsm() -> Any:
    return MagicMock(clear=AsyncMock(), get_data=AsyncMock(return_value={}))


@pytest.mark.asyncio
async def test_admin_callback_runs_for_configured_admin() -> None:
    router = create_admin_router(_app_state([1]))
    handler = _handler(router, "cancel_close")
    cb = _callback(1, "close_no")
    await handler(cb)
    cb.message.edit_text.assert_awaited_once_with("Оставлено.")


@pytest.mark.asyncio
async def test_admin_callback_blocked_for_non_admin() -> None:
    router = create_admin_router(_app_state([1]))
    handler = _handler(router, "cancel_close")
    cb = _callback(999, "close_no")
    await handler(cb)
    cb.message.edit_text.assert_not_awaited()
    cb.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_stateful_admin_callback_blocked_for_non_admin() -> None:
    router = create_admin_router(_app_state([1]))
    handler = _handler(router, "cancel_order")
    cb = _callback(999, "order_cancel")
    await handler(cb, _fsm())
    cb.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_authorised_user_becomes_admin() -> None:
    """A user who proved the admin password must pass ``is_admin`` for callbacks too."""
    router = create_admin_router(_app_state([1]))
    check_password = _message_handler(router, "check_password")
    uid = 2
    await check_password(_message(uid, "secret"), _fsm())

    handler = _handler(router, "cancel_close")
    cb = _callback(uid, "close_no")
    await handler(cb)
    cb.message.edit_text.assert_awaited_once_with("Оставлено.")
