from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OrderCreate(StatesGroup):
    entering_number = State()
    entering_client = State()
    entering_title = State()
    choosing_status = State()
    confirming = State()


class OrderCheck(StatesGroup):
    entering_number = State()


class AdminAuth(StatesGroup):
    waiting_password = State()
