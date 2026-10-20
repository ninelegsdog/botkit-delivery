from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.bot_factory import AppState
from src.core.callbacks import parse_callback_int
from src.core.fsm import OrderCheck
from src.core.nav import client_menu
from src.core.ui import escape
from src.delivery import service, texts


def create_delivery_router(app_state: AppState) -> Router:
    router = Router()
    db = app_state.db

    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            texts.WELCOME,
            reply_markup=client_menu(),
        )

    @router.message(F.text == "🔍 Проверить заказ")
    async def start_check(message: Message, state: FSMContext) -> None:
        await state.set_state(OrderCheck.entering_number)
        await message.answer(texts.ENTER_ORDER_NUMBER)

    @router.message(OrderCheck.entering_number)
    async def check_order(message: Message, state: FSMContext) -> None:
        number = message.text or ""
        order = await service.get_order_by_number(db, number)
        if not order:
            await message.answer(texts.ORDER_NOT_FOUND)
            return
        await state.clear()
        history = await service.get_order_history(db, int(order["id"]))
        history_text = (
            "\n".join(f"• {h['changed_at']} — {escape(str(h.get('status_name', '')))}" for h in history)
            if history
            else texts.NO_HISTORY
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=texts.BTN_SUBSCRIBE, callback_data=f"sub:{order['id']}"),
                    InlineKeyboardButton(text=texts.BTN_UNSUBSCRIBE, callback_data=f"unsub:{order['id']}"),
                ]
            ]
        )
        await message.answer(
            texts.order_card(
                escape(str(order.get("number", ""))),
                escape(str(order.get("title", ""))),
                escape(str(order.get("status_name", ""))),
                history_text,
            ),
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("sub:"))
    async def subscribe(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = parse_callback_int(callback.data, "sub:")
        if order_id is None:
            await callback.answer(texts.BAD_REQUEST, show_alert=True)
            return
        await service.subscribe_order(db, order_id, callback.from_user.id)
        await callback.message.edit_text(texts.SUBSCRIBED)  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("unsub:"))
    async def unsubscribe(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = parse_callback_int(callback.data, "unsub:")
        if order_id is None:
            await callback.answer(texts.BAD_REQUEST, show_alert=True)
            return
        await service.unsubscribe_order(db, order_id, callback.from_user.id)
        await callback.message.edit_text(texts.UNSUBSCRIBED)  # type: ignore[union-attr]
        await callback.answer()

    return router
