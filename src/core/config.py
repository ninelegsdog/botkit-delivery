from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str = ""
    admin_password: str = "admin123"
    db_path: str = "delivery.db"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    sentry_dsn: str = ""
    metrics_port: int = 8088

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            admin_password=os.getenv("ADMIN_PASSWORD", "admin123"),
            db_path=os.getenv("DB_PATH", "delivery.db"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            sentry_dsn=os.getenv("SENTRY_DSN", ""),
            metrics_port=int(os.getenv("METRICS_PORT", "8088")),
        )
