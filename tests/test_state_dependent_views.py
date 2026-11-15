"""State-dependent view tests for delivery."""

from __future__ import annotations

import pytest

from src.delivery import service


@pytest.mark.asyncio
async def test_statuses_empty_vs_populated(db):
    # migrate seeds default statuses
    statuses = await service.get_statuses(db)
    assert len(statuses) >= 4  # default statuses seeded


@pytest.mark.asyncio
async def test_order_missing_vs_present(db):
    assert await service.get_order(db, 99999) is None
    assert await service.get_order_by_number(db, "NOPE") is None

    order_id = await service.create_order(db, number="ORD-1", title="Test order", status_id=1)
    order = await service.get_order(db, order_id)
    assert order is not None
    assert order["number"] == "ORD-1"

    by_num = await service.get_order_by_number(db, "ORD-1")
    assert by_num is not None


@pytest.mark.asyncio
async def test_active_orders_empty_vs_populated(db):
    assert await service.get_active_orders(db) == []

    await service.create_order(db, number="ORD-1", title="O1", status_id=1)
    orders = await service.get_active_orders(db)
    assert len(orders) == 1


@pytest.mark.asyncio
async def test_order_history_empty_vs_populated(db):
    order_id = await service.create_order(db, number="ORD-1", title="O1", status_id=1)
    assert await service.get_order_history(db, order_id) == []

    await service.update_order_status(db, order_id=order_id, new_status_id=2, changed_by=1)
    history = await service.get_order_history(db, order_id)
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_order_count(db):
    assert await service.get_order_count(db) == 0
    await service.create_order(db, number="ORD-1", title="O1", status_id=1)
    assert await service.get_order_count(db) == 1


@pytest.mark.asyncio
async def test_subscribers_empty_vs_populated(db):
    order_id = await service.create_order(db, number="ORD-1", title="O1", status_id=1)
    assert await service.get_order_subscribers(db, order_id) == []

    await service.subscribe_order(db, order_id, user_id=5)
    subs = await service.get_order_subscribers(db, order_id)
    assert 5 in subs
