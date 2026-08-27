from __future__ import annotations

import pytest

from src.delivery import service


@pytest.mark.asyncio
async def test_get_statuses(db):
    statuses = await service.get_statuses(db)
    assert len(statuses) == 4


@pytest.mark.asyncio
async def test_get_status(db):
    statuses = await service.get_statuses(db)
    status = await service.get_status(db, int(statuses[0]["id"]))
    assert status is not None


@pytest.mark.asyncio
async def test_is_valid_transition(db):
    statuses = await service.get_statuses(db)
    ok = await service.is_valid_transition(db, int(statuses[0]["id"]), int(statuses[1]["id"]))
    assert ok


@pytest.mark.asyncio
async def test_is_invalid_transition(db):
    statuses = await service.get_statuses(db)
    ok = await service.is_valid_transition(db, int(statuses[3]["id"]), int(statuses[0]["id"]))
    assert not ok


@pytest.mark.asyncio
async def test_get_next_status(db):
    statuses = await service.get_statuses(db)
    next_st = await service.get_next_status(db, int(statuses[0]["id"]))
    assert next_st is not None
    assert next_st["name"] == statuses[1]["name"]


@pytest.mark.asyncio
async def test_create_order(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-001", title="Test order", status_id=int(statuses[0]["id"]))
    assert order_id > 0


@pytest.mark.asyncio
async def test_get_order_by_number(db):
    statuses = await service.get_statuses(db)
    await service.create_order(db, number="ORD-002", title="Test order", status_id=int(statuses[0]["id"]))
    order = await service.get_order_by_number(db, "ORD-002")
    assert order is not None
    assert order["number"] == "ORD-002"


@pytest.mark.asyncio
async def test_update_order_status(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-003", title="Test order", status_id=int(statuses[0]["id"]))
    ok = await service.update_order_status(db, order_id, int(statuses[1]["id"]))
    assert ok


@pytest.mark.asyncio
async def test_get_order_history(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-004", title="Test order", status_id=int(statuses[0]["id"]))
    await service.update_order_status(db, order_id, int(statuses[1]["id"]))
    history = await service.get_order_history(db, order_id)
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_subscribe_order(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-005", title="Test order", status_id=int(statuses[0]["id"]))
    await service.subscribe_order(db, order_id, 123)
    subscribers = await service.get_order_subscribers(db, order_id)
    assert 123 in subscribers


@pytest.mark.asyncio
async def test_unsubscribe_order(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-006", title="Test order", status_id=int(statuses[0]["id"]))
    await service.subscribe_order(db, order_id, 123)
    await service.unsubscribe_order(db, order_id, 123)
    subscribers = await service.get_order_subscribers(db, order_id)
    assert 123 not in subscribers


@pytest.mark.asyncio
async def test_close_order(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(db, number="ORD-007", title="Test order", status_id=int(statuses[0]["id"]))
    await service.close_order(db, order_id)
    order = await service.get_order(db, order_id)
    assert order is not None


@pytest.mark.asyncio
async def test_get_order_count(db):
    statuses = await service.get_statuses(db)
    await service.create_order(db, number="ORD-008", title="Test order", status_id=int(statuses[0]["id"]))
    count = await service.get_order_count(db)
    assert count == 1


@pytest.mark.asyncio
async def test_get_status_stats(db):
    statuses = await service.get_statuses(db)
    await service.create_order(db, number="ORD-009", title="Test order", status_id=int(statuses[0]["id"]))
    stats = await service.get_status_stats(db)
    assert len(stats) == 4
