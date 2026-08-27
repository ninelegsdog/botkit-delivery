from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.core.database import Database


async def get_statuses(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(text("SELECT * FROM statuses WHERE is_active = 1 ORDER BY position"))
        return [dict(r) for r in result.mappings().all()]


async def get_status(db: Database, status_id: int) -> dict[str, Any] | None:
    async with db.session() as session:
        result = await session.execute(text("SELECT * FROM statuses WHERE id = :id"), {"id": status_id})
        row = result.mappings().fetchone()
        return dict(row) if row else None


async def is_valid_transition(db: Database, from_status_id: int, to_status_id: int) -> bool:
    async with db.session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM status_transitions WHERE from_status_id = :from_id AND to_status_id = :to_id"),
            {"from_id": from_status_id, "to_id": to_status_id},
        )
        row = result.fetchone()
        return int(row[0]) > 0 if row else False


async def get_next_status(db: Database, current_status_id: int) -> dict[str, Any] | None:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT s.* FROM statuses s "
                "JOIN status_transitions st ON s.id = st.to_status_id "
                "WHERE st.from_status_id = :sid AND s.is_active = 1"
            ),
            {"sid": current_status_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


async def create_order(
    db: Database,
    *,
    number: str,
    client_user_id: int | None = None,
    client_label: str | None = None,
    title: str,
    status_id: int,
) -> int:
    async with db.transaction() as session:
        result = await session.execute(
            text(
                "INSERT INTO orders (number, client_user_id, client_label, title, status_id) "
                "VALUES (:num, :cid, :clbl, :title, :sid)"
            ),
            {"num": number, "cid": client_user_id, "clbl": client_label, "title": title, "sid": status_id},
        )
        order_id = result.lastrowid  # type: ignore[attr-defined]
        assert order_id is not None
        return int(order_id)


async def get_order_by_number(db: Database, number: str) -> dict[str, Any] | None:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT o.*, s.name as status_name FROM orders o "
                "JOIN statuses s ON o.status_id = s.id "
                "WHERE o.number = :num AND o.is_active = 1"
            ),
            {"num": number},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


async def get_order(db: Database, order_id: int) -> dict[str, Any] | None:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT o.*, s.name as status_name FROM orders o JOIN statuses s ON o.status_id = s.id WHERE o.id = :id"
            ),
            {"id": order_id},
        )
        row = result.mappings().fetchone()
        return dict(row) if row else None


async def get_active_orders(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT o.*, s.name as status_name FROM orders o "
                "JOIN statuses s ON o.status_id = s.id "
                "WHERE o.is_active = 1 ORDER BY o.created_at DESC"
            )
        )
        return [dict(r) for r in result.mappings().all()]


async def update_order_status(
    db: Database, order_id: int, new_status_id: int, changed_by: int | None = None, comment: str | None = None
) -> bool:
    async with db.transaction() as session:
        result = await session.execute(
            text("UPDATE orders SET status_id = :sid, version = version + 1 WHERE id = :oid AND is_active = 1"),
            {"sid": new_status_id, "oid": order_id},
        )
        rowcount = result.rowcount  # type: ignore[attr-defined]
        if rowcount and int(rowcount) > 0:
            await session.execute(
                text(
                    "INSERT INTO order_status_history (order_id, status_id, comment, changed_by) "
                    "VALUES (:oid, :sid, :comment, :changed_by)"
                ),
                {"oid": order_id, "sid": new_status_id, "comment": comment, "changed_by": changed_by},
            )
            return True
        return False


async def close_order(db: Database, order_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(text("UPDATE orders SET is_active = 0 WHERE id = :id"), {"id": order_id})


async def get_order_history(db: Database, order_id: int) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT h.*, s.name as status_name FROM order_status_history h "
                "JOIN statuses s ON h.status_id = s.id "
                "WHERE h.order_id = :oid ORDER BY h.changed_at"
            ),
            {"oid": order_id},
        )
        return [dict(r) for r in result.mappings().all()]


async def subscribe_order(db: Database, order_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text("INSERT OR REPLACE INTO subscriptions (order_id, user_id, is_active) VALUES (:oid, :uid, 1)"),
            {"oid": order_id, "uid": user_id},
        )


async def unsubscribe_order(db: Database, order_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text("UPDATE subscriptions SET is_active = 0 WHERE order_id = :oid AND user_id = :uid"),
            {"oid": order_id, "uid": user_id},
        )


async def get_order_subscribers(db: Database, order_id: int) -> list[int]:
    async with db.session() as session:
        result = await session.execute(
            text("SELECT user_id FROM subscriptions WHERE order_id = :oid AND is_active = 1"),
            {"oid": order_id},
        )
        return [int(r[0]) for r in result.all()]


async def get_order_count(db: Database) -> int:
    async with db.session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM orders WHERE is_active = 1"))
        row = result.fetchone()
        return int(row[0]) if row else 0


async def get_status_stats(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT s.name, COUNT(o.id) as cnt FROM statuses s "
                "LEFT JOIN orders o ON s.id = o.status_id AND o.is_active = 1 "
                "WHERE s.is_active = 1 GROUP BY s.id ORDER BY s.position"
            )
        )
        return [dict(r) for r in result.mappings().all()]
