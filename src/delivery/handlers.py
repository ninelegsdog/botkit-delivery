from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.bot_factory import AppState
from src.core.fsm import OrderCheck
from src.core.nav import client_menu
from src.core.ui import escape
from src.delivery import service


def create_delivery_router(app_state: AppState) -> Router:
    router = Router()
    db = app_state.db

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "📦 Отслеживание заказов и доставок!",
            reply_markup=client_menu(),
        )

    @router.message(F.text == "🔍 Проверить заказ")
    async def start_check(message: Message, state: FSMContext) -> None:
        await state.set_state(OrderCheck.entering_number)
        await message.answer("🔍 Введите номер заказа:")

    @router.message(OrderCheck.entering_number)
    async def check_order(message: Message, state: FSMContext) -> None:
        number = message.text or ""
        order = await service.get_order_by_number(db, number)
        if not order:
            await message.answer("❌ Заказ не найден. Проверьте номер.")
            return
        await state.clear()
        history = await service.get_order_history(db, int(order["id"]))
        history_text = "\n".join(
            f"• {h['changed_at']} — {escape(str(h.get('status_name', '')))}"
            for h in history
        ) if history else "Нет истории"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔔 Следить", callback_data=f"sub:{order['id']}"),
                    InlineKeyboardButton(text="🔕 Не следить", callback_data=f"unsub:{order['id']}"),
                ]
            ]
        )
        await message.answer(
            f"📦 Заказ #{escape(str(order.get('number', '')))}\n"
            f"Название: {escape(str(order.get('title', '')))}\n"
            f"Статус: {escape(str(order.get('status_name', '')))}\n\n"
            f"📜 История:\n{history_text}",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("sub:"))
    async def subscribe(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = int(callback.data.split(":")[1])
        await service.subscribe_order(db, order_id, callback.from_user.id)
        await callback.message.edit_text("🔔 Вы следите за этим заказом.")  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("unsub:"))
    async def unsubscribe(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = int(callback.data.split(":")[1])
        await service.unsubscribe_order(db, order_id, callback.from_user.id)
        await callback.message.edit_text("🔕 Вы отписались от уведомлений.")  # type: ignore[union-attr]
        await callback.answer()

    return router
