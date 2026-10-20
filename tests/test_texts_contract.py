"""Тексты бота: константы существуют, хелперы подставляют свои аргументы.

Зачем
=====

`src/delivery/texts.py` — единый источник строк, которые бот отправляет. Тест
держит две вещи:

1. **Константы на месте и непусты.** Обработчик, отдавший пустую строку, —
   молчаливый дефект: пользователь видит пузырь без текста, а тест на поведение
   (если он сверяет вхождение) проходит.
2. **Хелперы действительно подставляют переданное.** Правка, выбросившая аргумент
   (`#{number}` → `#{}`, статус → литерал), иначе прошла бы незамеченной: строка
   всё ещё «есть».

Каждая проверка имеет негативного близнеца: сломай подстановку — тест красный.
"""

from __future__ import annotations

import pytest

from src.delivery import texts

CONSTANTS = [
    texts.WELCOME,
    texts.ENTER_ORDER_NUMBER,
    texts.ORDER_NOT_FOUND,
    texts.NO_HISTORY,
    texts.SUBSCRIBED,
    texts.UNSUBSCRIBED,
    texts.ASK_PASSWORD,
    texts.ADMIN_WELCOME,
    texts.BAD_PASSWORD,
    texts.TOO_MANY_ATTEMPTS,
    texts.ENTER_NUMBER,
    texts.ENTER_CLIENT,
    texts.ENTER_TITLE,
    texts.NO_STATUSES,
    texts.CHOOSE_INITIAL_STATUS,
    texts.ORDER_CREATED,
    texts.CANCELLED,
    texts.CHOOSE_ACTION,
    texts.NO_ORDERS,
    texts.ORDER_MISSING,
    texts.FINAL_STATUS,
    texts.CONFIRM_CLOSE,
    texts.ORDER_CLOSED,
    texts.CLOSE_DECLINED,
    texts.BAD_REQUEST,
]

BUTTON_LABELS = [
    texts.BTN_CHECK_ORDER,
    texts.BTN_SUBSCRIBE,
    texts.BTN_UNSUBSCRIBE,
    texts.BTN_NEW_ORDER,
    texts.BTN_ORDERS,
    texts.BTN_STATS,
    texts.BTN_CREATE,
    texts.BTN_CANCEL,
    texts.BTN_NEXT,
    texts.BTN_CLOSE,
    texts.BTN_YES,
    texts.BTN_NO,
]


@pytest.mark.parametrize("value", CONSTANTS, ids=lambda v: v[:24])
def test_текст_непуст(value: str) -> None:
    """Пустой ответ — пузырь без текста; пользователь не поймёт, что случилось."""
    assert value.strip(), "текст сообщения пуст или из пробелов"


@pytest.mark.parametrize("label", BUTTON_LABELS, ids=lambda v: v[:24])
def test_подпись_кнопки_непуста(label: str) -> None:
    """Кнопка без подписи неотличима от декоративного разделителя."""
    assert label.strip(), "подпись кнопки пуста"


def test_все_подписи_кнопок_уникальны() -> None:
    """Две кнопки с одной подписью — пользователь нажмёт не ту.

    Обработчики выше различают кнопки по тексту (`F.text == ...`), так что
    совпадение подписей ломает маршрутизацию, а не только вид.
    """
    duplicates = {x for x in BUTTON_LABELS if BUTTON_LABELS.count(x) > 1}
    assert not duplicates, f"дубли подписей кнопок: {duplicates}"


def test_приветствие_содержит_подстроку_из_кейсов() -> None:
    """Кейс фермы и e2e-тест цитируют подстроку без эмодзи — она обязана быть.

    `text_contains` сверяет вхождение, поэтому ведущий эмодзи правке не мешает,
    но сама фраза обязана остаться: это тот текст, который ловят оба пути.
    """
    assert "Отслеживание заказов и доставок" in texts.WELCOME


# ── хелперы: подстановка аргумента, а не литерал ────────────────────────────


def test_order_card_подставляет_поля_и_историю() -> None:
    """Карточка без номера, названия или истории — не то, что искал клиент."""
    got = texts.order_card("A-1", "Кроссовки", "В пути", "• 10:00 — принят")
    assert "#A-1" in got, got
    assert "Кроссовки" in got, got
    assert "В пути" in got, got
    assert "10:00 — принят" in got, got


def test_order_card_чужой_номер_меняет_строку() -> None:
    """Негативный близнец: фиксированный номер прошёл бы первую проверку."""
    assert texts.order_card("A", "X", "Y", "Z") != texts.order_card("B", "X", "Y", "Z")


def test_confirm_create_несёт_номер_клиента_название() -> None:
    """На шаге подтверждения пользователь видит ровно то, что попадёт в базу."""
    got = texts.confirm_create("A-1", "@ivan", "Кроссовки")
    assert "#A-1" in got and "@ivan" in got and "Кроссовки" in got, got


def test_order_created_различает_заказы() -> None:
    """Номер в подтверждении — не украшение, а адрес заказа."""
    assert texts.order_created("A-1") != texts.order_created("A-2")


def test_status_updated_вставляет_имя_статуса() -> None:
    """Литерал вместо имени статуса показал бы менеджеру ложное состояние."""
    got = texts.status_updated("Доставлен")
    assert "Доставлен" in got, got


def test_order_stats_различает_число_и_разбивку() -> None:
    """Статистика, где счётчик и разбивка совпали, — одна цифра под двумя ярлыками."""
    got = texts.order_stats(7, "  Новый: 3\n  В пути: 4")
    assert "7" in got and "Новый: 3" in got and "В пути: 4" in got, got
