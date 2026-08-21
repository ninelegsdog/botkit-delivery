from __future__ import annotations

from src.admin.handlers import create_admin_router
from src.core.bot_factory import AppState
from src.delivery.handlers import create_delivery_router


def register_routers(state: AppState) -> None:
    state.dp.include_router(create_delivery_router(state))
    state.dp.include_router(create_admin_router(state))
