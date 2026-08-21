from __future__ import annotations

import html
from typing import Any


def escape(text: str | None) -> str:
    return html.escape(str(text)) if text else ""


def order_card(order: dict[str, Any]) -> str:
    status = str(order.get("status_name", order.get("status_id", "")))
    return (
        f"📦 Заказ #{escape(str(order.get('number', '')))}\n"
        f"Название: {escape(str(order.get('title', '')))}\n"
        f"Статус: {escape(status)}"
    )
