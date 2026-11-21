from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database.db import get_user_bookings, get_booking, delete_booking
from handlers.booking import pretty_date
from utils import notify_admin

router = Router()


async def build_list(user_id: int):
    """Собирает текст списка записей и кнопки «Отменить»."""
    bookings = await get_user_bookings(user_id, date.today().isoformat())

    if not bookings:
        return (
            "У вас пока нет активных записей.\n"
            "Нажмите «📅 Записаться», чтобы выбрать время.",
            None,
        )

    lines = ["📋 Ваши записи:\n"]
    rows = []
    for b in bookings:
        lines.append(f"• {pretty_date(b['date'])} в {b['time']} — {b['service']}")
        short_date = pretty_date(b["date"])[:5]  # "21.11.2026" -> "21.11"
        rows.append([
            InlineKeyboardButton(
                text=f"❌ Отменить {short_date} {b['time']}",
                callback_data=f"mybk_cancel:{b['id']}",
            )
        ])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "📋 Мои записи")
async def show_my_bookings(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await build_list(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("mybk_cancel:"))
async def ask_confirm(callback: CallbackQuery):
    """Шаг 1 отмены: спрашиваем «Точно отменить?»"""
    booking_id = int(callback.data.split(":")[1])
    booking = await get_booking(booking_id)

    if booking is None or booking["user_id"] != callback.from_user.id:
        await callback.answer("Эта запись уже не найдена.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"mybk_yes:{booking_id}"),
        InlineKeyboardButton(text="⬅️ Нет", callback_data="mybk_no"),
    ]])
    await callback.message.edit_text(
        "Отменить эту запись?\n\n"
        f"Услуга: {booking['service']}\n"
        f"Дата: {pretty_date(booking['date'])}\n"
        f"Время: {booking['time']}",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mybk_yes:"))
async def confirm_cancel(callback: CallbackQuery):
    """Шаг 2 отмены: человек нажал «Да»."""
    booking_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    booking = await get_booking(booking_id)

    # Защита: запись должна существовать и принадлежать этому человеку
    if booking is None or booking["user_id"] != user_id:
        await callback.answer("Эта запись уже не найдена.", show_alert=True)
        return

    await delete_booking(booking_id, user_id)

    await notify_admin(
        callback.bot,
        f"❌ Запись #{booking_id} отменена клиентом\n\n"
        f"Услуга: {booking['service']}\n"
        f"Дата: {pretty_date(booking['date'])}\n"
        f"Время: {booking['time']}\n"
        f"Имя: {booking['name']}\n"
        f"Телефон: {booking['phone']}",
    )

    text, kb = await build_list(user_id)
    await callback.message.edit_text("✅ Запись отменена.\n\n" + text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "mybk_no")
async def keep_booking(callback: CallbackQuery):
    """Человек передумал: возвращаем список."""
    text, kb = await build_list(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()