from __future__ import annotations

import pytest

from src.core.config import Config
from src.core.ui import escape, order_card


@pytest.mark.asyncio
async def test_config_from_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test_token")
    config = Config.from_env()
    assert config.bot_token == "test_token"


def test_escape():
    assert escape("<script>") == "&lt;script&gt;"
    assert escape("hello") == "hello"
    assert escape(None) == ""


def test_order_card():
    card = order_card(
        {
            "number": "123",
            "title": "Test <order>",
            "status_name": "Принят",
        }
    )
    assert "<order>" not in card
    assert "123" in card
    assert "Принят" in card
