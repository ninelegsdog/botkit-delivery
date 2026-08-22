from __future__ import annotations

import asyncio
import logging

from src.app import register_routers
from src.core.auth import AuthMiddleware
from src.core.bot_factory import create_app
from src.core.errors import RetryMiddleware, register_error_handler
from src.core.metrics import UpdatesMiddleware, start_metrics_server
from src.core.migrations import migrate
from src.core.sentry import init_sentry
from src.core.throttling import ThrottlingMiddleware
from src.delivery.webhook_api import create_webhook_app


async def main() -> None:
    state = create_app()
    init_sentry(state.config.sentry_dsn)
    await migrate(state.db)
    state.dp.message.middleware(AuthMiddleware(state.db))
    state.dp.message.middleware(ThrottlingMiddleware())
    state.dp.callback_query.middleware(AuthMiddleware(state.db))
    state.dp.update.outer_middleware(UpdatesMiddleware())
    state.dp.message.middleware(RetryMiddleware())
    register_error_handler(state.dp)
    register_routers(state)
    logging.basicConfig(level=state.config.log_level)
    await state.bot.delete_webhook(drop_pending_updates=True)
    runner = await start_metrics_server(state.config.metrics_port)
    wh_runner = None
    if state.config.webhook_secret:
        from aiohttp.web import AppRunner, TCPSite

        wh_runner = AppRunner(create_webhook_app(state))
        await wh_runner.setup()
        site = TCPSite(wh_runner, "0.0.0.0", 8089)
        await site.start()
    try:
        await state.dp.start_polling(state.bot)
    finally:
        if wh_runner:
            await wh_runner.cleanup()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
