from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.delivery import texts


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_CHECK_ORDER)],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.BTN_NEW_ORDER), KeyboardButton(text=texts.BTN_ORDERS)],
            [KeyboardButton(text=texts.BTN_STATS)],
        ],
        resize_keyboard=True,
    )
