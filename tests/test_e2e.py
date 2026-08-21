from __future__ import annotations

import pytest

from src.core.ui import order_card
from src.delivery import service


@pytest.mark.asyncio
async def test_full_order_lifecycle(db):
    statuses = await service.get_statuses(db)
    order_id = await service.create_order(
        db, number="ORD-100", client_label="Иванов",
        title="Ремонт телефона", status_id=int(statuses[0]["id"])
    )
    assert order_id > 0

    order = await service.get_order_by_number(db, "ORD-100")
    assert order is not None
    assert order["status_name"] == "Принят"

    next_st = await service.get_next_status(db, int(statuses[0]["id"]))
    assert next_st is not None
    await service.update_order_status(db, order_id, int(next_st["id"]))

    order = await service.get_order(db, order_id)
    assert order is not None
    assert order["status_name"] == next_st["name"]

    history = await service.get_order_history(db, order_id)
    assert len(history) >= 1

    await service.subscribe_order(db, order_id, 111)
    subscribers = await service.get_order_subscribers(db, order_id)
    assert 111 in subscribers

    await service.unsubscribe_order(db, order_id, 111)
    subscribers = await service.get_order_subscribers(db, order_id)
    assert 111 not in subscribers

    await service.close_order(db, order_id)


@pytest.mark.asyncio
async def test_status_transition_validation(db):
    statuses = await service.get_statuses(db)
    ok = await service.is_valid_transition(db, int(statuses[0]["id"]), int(statuses[1]["id"]))
    assert ok

    ok = await service.is_valid_transition(db, int(statuses[3]["id"]), int(statuses[0]["id"]))
    assert not ok


@pytest.mark.asyncio
async def test_order_card_html():
    card = order_card({
        "number": "123",
        "title": "Test <script>",
        "status_name": "Принят",
    })
    assert "<script>" not in card
    assert "123" in card
