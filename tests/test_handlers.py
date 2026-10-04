from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from src.app import register_routers
from src.core.bot_factory import create_app
from src.core.config import Config


@pytest.fixture
def app_state() -> Any:
    cfg = Config(
        bot_token="123456789:AAfake",
        admin_password="secret",
        admin_ids=[1],
        redis_url="redis://localhost:6379/0",
    )
    with patch("src.core.bot_factory.RedisStorage.from_url", return_value=MemoryStorage()):
        state = create_app(cfg)
    state.dp = Dispatcher(storage=MemoryStorage())
    return state


def _sent_text(bot: Bot) -> str:
    for call in bot.session.make_request.call_args_list:
        payload = call.args[1] if len(call.args) >= 2 else call.kwargs.get("data")
        text = getattr(payload, "text", None) if not isinstance(payload, dict) else payload.get("text")
        if text:
            return text
    raise AssertionError("no message was sent")


@pytest.mark.asyncio
async def test_start_command(app_state: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text="/start",
    )
    update = Update(update_id=1, message=message)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
        await app_state.dp.feed_update(bot, update)
        assert mock_req.await_count >= 1
        assert "Отслеживание заказов" in _sent_text(bot)


@pytest.mark.asyncio
async def test_admin_panel(app_state: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text="/admin",
    )
    update = Update(update_id=1, message=message)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
        await app_state.dp.feed_update(bot, update)
        assert mock_req.await_count >= 1
        assert "Введите пароль" in _sent_text(bot)


@pytest.mark.asyncio
async def test_create_delivery_router_start_clears_fsm_state() -> None:
    """Пользователь был посреди сценария: /start обязан сбросить состояние."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.types import User

    from src.core.fsm import OrderCheck
    from src.delivery.handlers import create_delivery_router

    router = create_delivery_router(SimpleNamespace(db=MagicMock()))
    handler = next(
        (h.callback for h in router.message.handlers if getattr(h.callback, "__name__", None) == "cmd_start"),
        None,
    )
    assert handler is not None, "обработчик cmd_start не найден"

    fsm_ctx = FSMContext(MemoryStorage(), StorageKey(bot_id=0, chat_id=1, user_id=1))
    await fsm_ctx.set_state(OrderCheck.entering_number)
    assert await fsm_ctx.get_state() is not None

    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.from_user = User(id=1, is_bot=False, first_name="Test")
    await handler(msg, fsm_ctx)

    assert await fsm_ctx.get_state() is None
