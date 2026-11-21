from datetime import date, timedelta

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import ADMIN_ID
from database.db import get_bookings_by_date, get_upcoming_bookings
from handlers.booking import pretty_date

router = Router()

# Все обработчики этого файла работают только для администратора
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📆 Сегодня", callback_data="adm:today"),
            InlineKeyboardButton(text="🌅 Завтра", callback_data="adm:tomorrow"),
        ],
        [InlineKeyboardButton(text="📋 Ближайшие записи", callback_data="adm:upcoming")],
    ])


def format_bookings(title: str, bookings: list, show_date: bool = False) -> str:
    """Превращает список записей в аккуратный текст."""
    if not bookings:
        return f"{title}\n\nЗаписей нет."

    lines = [title, ""]
    for b in bookings:
        if show_date:
            when = f"{pretty_date(b['date'])[:5]} {b['time']}"  # "21.11 14:00"
        else:
            when = b["time"]
        lines.append(f"🕒 {when} — {b['service']}")
        lines.append(f"    👤 {b['name']}, {b['phone']}")
    return "\n".join(lines)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛠 Панель администратора\nВыберите, что показать:",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data.startswith("adm:"))
async def admin_show(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    today = date.today()

    if action == "today":
        bookings = await get_bookings_by_date(today.isoformat())
        text = format_bookings(f"📆 Записи на сегодня ({today.strftime('%d.%m')})", bookings)
    elif action == "tomorrow":
        tomorrow = today + timedelta(days=1)
        bookings = await get_bookings_by_date(tomorrow.isoformat())
        text = format_bookings(f"🌅 Записи на завтра ({tomorrow.strftime('%d.%m')})", bookings)
    else:
        bookings = await get_upcoming_bookings(today.isoformat())
        text = format_bookings("📋 Ближайшие записи", bookings, show_date=True)

    try:
        await callback.message.edit_text(text, reply_markup=admin_kb())
    except TelegramBadRequest:
        pass  # нажали ту же кнопку повторно, текст не изменился
    await callback.answer()