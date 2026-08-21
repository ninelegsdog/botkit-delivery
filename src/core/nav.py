from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Проверить заказ")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новый заказ"), KeyboardButton(text="📦 Заказы")],
            [KeyboardButton(text="⚙️ Статусы"), KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True,
    )
