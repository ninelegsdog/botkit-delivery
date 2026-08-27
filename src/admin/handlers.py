from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.bot_factory import AppState
from src.core.fsm import AdminAuth, OrderCreate
from src.core.nav import admin_menu, client_menu
from src.core.ui import escape, order_card
from src.delivery import service


def create_admin_router(app_state: AppState) -> Router:
    router = Router()
    db = app_state.db

    def is_admin(user_id: int) -> bool:
        return user_id in (app_state.config.admin_ids or [])

    @router.message(Command("admin"))
    async def cmd_admin(message: Message, state: FSMContext) -> None:
        await state.set_state(AdminAuth.waiting_password)
        await message.answer("🔑 Введите пароль:")

    @router.message(AdminAuth.waiting_password)
    async def check_password(message: Message, state: FSMContext) -> None:
        if message.text == app_state.config.admin_password:
            await state.clear()
            await message.answer("✅ Добро пожаловать!", reply_markup=admin_menu())
        else:
            await state.clear()
            await message.answer("❌ Неверный пароль.", reply_markup=client_menu())

    @router.message(F.text == "➕ Новый заказ")
    async def start_new_order(message: Message, state: FSMContext) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        await state.set_state(OrderCreate.entering_number)
        await message.answer("📋 Номер заказа:")

    @router.message(OrderCreate.entering_number)
    async def enter_order_number(message: Message, state: FSMContext) -> None:
        await state.update_data(number=message.text or "")
        await state.set_state(OrderCreate.entering_client)
        await message.answer("👤 Клиент (username или user_id):")

    @router.message(OrderCreate.entering_client)
    async def enter_order_client(message: Message, state: FSMContext) -> None:
        await state.update_data(client=message.text or "")
        await state.set_state(OrderCreate.entering_title)
        await message.answer("📝 Название заказа:")

    @router.message(OrderCreate.entering_title)
    async def enter_order_title(message: Message, state: FSMContext) -> None:
        await state.update_data(title=message.text or "")
        statuses = await service.get_statuses(db)
        if not statuses:
            await message.answer("❌ Нет статусов. Настройте статусы.")
            await state.clear()
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s["name"], callback_data=f"os:{s['id']}")]
                for s in statuses
            ]
        )
        await state.set_state(OrderCreate.choosing_status)
        await message.answer("📊 Начальный статус:", reply_markup=kb)

    @router.callback_query(F.data.startswith("os:"), OrderCreate.choosing_status)
    async def choose_status(callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.data:
            return
        status_id = int(callback.data.split(":")[1])
        await state.update_data(status_id=status_id)
        data = await state.get_data()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Создать", callback_data="order_confirm"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="order_cancel"),
                ]
            ]
        )
        await state.set_state(OrderCreate.confirming)
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"Создать заказ?\n"
            f"📋 #{escape(str(data.get('number', '')))}\n"
            f"👤 {escape(str(data.get('client', '')))}\n"
            f"📝 {escape(str(data.get('title', '')))}",
            reply_markup=kb,
        )
        await callback.answer()

    @router.callback_query(F.data == "order_confirm", OrderCreate.confirming)
    async def confirm_order(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        await service.create_order(
            db,
            number=str(data.get("number", "")),
            client_label=str(data.get("client", "")),
            title=str(data.get("title", "")),
            status_id=int(str(data.get("status_id", 0))),
        )
        await state.clear()
        await callback.message.edit_text("✅ Заказ создан!")  # type: ignore[union-attr]
        await callback.answer()
        await callback.message.answer(f"📦 Заказ #{data.get('number', '')} создан.", reply_markup=admin_menu())  # type: ignore[union-attr]

    @router.callback_query(F.data == "order_cancel")
    async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.edit_text("Отменено.")  # type: ignore[union-attr]
        await callback.answer()
        await callback.message.answer("Выберите действие:", reply_markup=admin_menu())  # type: ignore[union-attr]

    @router.message(F.text == "📦 Заказы")
    async def list_orders(message: Message) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        orders = await service.get_active_orders(db)
        if not orders:
            await message.answer("Нет заказов.")
            return
        for o in orders[:10]:
            card = order_card(o)
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="▶️ Следующий", callback_data=f"next:{o['id']}"),
                        InlineKeyboardButton(text="✅ Закрыть", callback_data=f"close:{o['id']}"),
                    ]
                ]
            )
            await message.answer(card, reply_markup=kb)

    @router.callback_query(F.data.startswith("next:"))
    async def next_status(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = int(callback.data.split(":")[1])
        order = await service.get_order(db, order_id)
        if not order:
            await callback.answer("Заказ не найден.")
            return
        next_st = await service.get_next_status(db, int(order["status_id"]))
        if not next_st:
            await callback.message.edit_text("✅ Финальный статус достигнут.")  # type: ignore[union-attr]
            await callback.answer()
            return
        await service.update_order_status(db, order_id, int(next_st["id"]), callback.from_user.id)
        subscribers = await service.get_order_subscribers(db, order_id)
        for uid in subscribers:
            try:
                await app_state.bot.send_message(
                    uid,
                    f"📦 Заказ #{order['number']}: статус → {next_st['name']}",
                )
            except Exception:
                pass
        await callback.message.edit_text(f"✅ Статус обновлён: {next_st['name']}")  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("close:"))
    async def close_order(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = int(callback.data.split(":")[1])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data=f"close_yes:{order_id}"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="close_no"),
                ]
            ]
        )
        await callback.message.edit_text("❓ Закрыть заказ?", reply_markup=kb)  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("close_yes:"))
    async def confirm_close(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        order_id = int(callback.data.split(":")[1])
        await service.close_order(db, order_id)
        await callback.message.edit_text("✅ Заказ закрыт.")  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data == "close_no")
    async def cancel_close(callback: CallbackQuery) -> None:
        await callback.message.edit_text("Оставлено.")  # type: ignore[union-attr]
        await callback.answer()

    @router.message(F.text == "📊 Статистика")
    async def admin_stats(message: Message) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        count = await service.get_order_count(db)
        stats = await service.get_status_stats(db)
        lines = [f"  {escape(str(s['name']))}: {s['cnt']}" for s in stats]
        await message.answer(f"📊 Заказов: {count}\n\nПо статусам:\n" + "\n".join(lines))

    return router
