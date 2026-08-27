from __future__ import annotations

from sqlalchemy import text

from src.core.database import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS status_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_status_id INTEGER NOT NULL,
    to_status_id INTEGER NOT NULL,
    FOREIGN KEY (from_status_id) REFERENCES statuses(id),
    FOREIGN KEY (to_status_id) REFERENCES statuses(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL UNIQUE,
    client_user_id INTEGER,
    client_label TEXT,
    title TEXT NOT NULL,
    status_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (status_id) REFERENCES statuses(id)
);

CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    comment TEXT,
    changed_by INTEGER,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (status_id) REFERENCES statuses(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(order_id, user_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(number);
CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_order ON subscriptions(order_id, user_id);

CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    source_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(order_id, status_id, source_timestamp)
);
"""


async def migrate(db: Database) -> None:
    async with db.transaction() as conn:
        for statement in SCHEMA.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))
        existing = await conn.execute(text("SELECT COUNT(*) FROM statuses"))
        row = existing.fetchone()
        if row and int(row[0]) == 0:
            default_statuses = [
                ("Принят", 0),
                ("В работе", 1),
                ("Готов", 2),
                ("Выдан", 3),
            ]
            for name, pos in default_statuses:
                await conn.execute(
                    text("INSERT INTO statuses (name, position) VALUES (:name, :pos)"),
                    {"name": name, "pos": pos},
                )
            statuses = await conn.execute(text("SELECT id FROM statuses ORDER BY position"))
            ids = [r[0] for r in statuses.fetchall()]
            for i in range(len(ids) - 1):
                await conn.execute(
                    text("INSERT INTO status_transitions (from_status_id, to_status_id) VALUES (:from_id, :to_id)"),
                    {"from_id": ids[i], "to_id": ids[i + 1]},
                )
