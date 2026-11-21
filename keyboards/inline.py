from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SERVICES, SLOTS


def nav_buttons(back: bool = True) -> list:
    """Нижний ряд кнопок: «Назад» (если нужен) и «Отменить»."""
    row = []
    if back:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    row.append(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"))
    return row


def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, service in enumerate(SERVICES):
        builder.button(
            text=f"{service['name']} — {service['price']} ₽",
            callback_data=f"service:{index}",
        )
    builder.adjust(1)
    builder.row(*nav_buttons(back=False))  # на первом шаге «Назад» не нужен
    return builder.as_markup()


def free_slots(date_str: str, busy: list) -> list:
    """Оставляет только свободное время (и не прошедшее, если выбран сегодняшний день)."""
    now = datetime.now()
    result = []
    for slot in SLOTS:
        if slot in busy:
            continue
        if date_str == now.date().isoformat() and int(slot[:2]) <= now.hour:
            continue
        result.append(slot)
    return result


def times_kb(slots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"time:{slot}")
    builder.adjust(3)
    builder.row(*nav_buttons())
    return builder.as_markup()


def text_step_kb() -> InlineKeyboardMarkup:
    """Кнопки под шагами, где человек вводит текст (имя, телефон)."""
    return InlineKeyboardMarkup(inline_keyboard=[nav_buttons()])