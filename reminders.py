import asyncio
import logging
from datetime import date, datetime, timedelta

from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    REMINDER_HOURS,
    REMINDER_CHECK_SECONDS,
    SALON_NAME,
    SALON_ADDRESS,
)
from database.db import get_pending_reminders, mark_reminded
from handlers.booking import pretty_date

router = Router()


def reminder_kb(booking_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Приду", callback_data="remind_ok"),
        # Эту кнопку уже обрабатывает раздел «Мои записи» (с вопросом «Точно отменить?»)
        InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"mybk_cancel:{booking_id}"),
    ]])


def reminder_text(booking: dict) -> str:
    return (
        f"⏰ Напоминание о записи в {SALON_NAME}\n\n"
        f"Услуга: {booking['service']}\n"
        f"Дата: {pretty_date(booking['date'])}\n"
        f"Время: {booking['time']}\n"
        f"Адрес: {SALON_ADDRESS}\n\n"
        "Подтвердите, пожалуйста, что придёте 💖"
    )


async def send_due_reminders(bot) -> None:
    """Один проход: находит записи, которым пора напомнить, и отправляет."""
    now = datetime.now()
    deadline = now + timedelta(hours=REMINDER_HOURS)

    for booking in await get_pending_reminders(date.today().isoformat()):
        visit = datetime.strptime(f"{booking['date']} {booking['time']}", "%Y-%m-%d %H:%M")

        # Напоминаем, только если визит ещё не прошёл и до него осталось не больше REMINDER_HOURS
        if not (now < visit <= deadline):
            continue

        try:
            await bot.send_message(
                booking["user_id"],
                reminder_text(booking),
                reply_markup=reminder_kb(booking["id"]),
            )
        except TelegramAPIError as error:
            # Например, клиент заблокировал бота. Не пытаемся бесконечно
            logging.warning("Не удалось отправить напоминание #%s: %s", booking["id"], error)

        await mark_reminded(booking["id"])


async def reminder_loop(bot) -> None:
    """Бесконечный цикл: проверяем, ждём минуту, проверяем снова."""
    while True:
        try:
            await send_due_reminders(bot)
        except Exception:
            # Любая ошибка не должна «убивать» напоминания
            logging.exception("Ошибка в цикле напоминаний")
        await asyncio.sleep(REMINDER_CHECK_SECONDS)


@router.callback_query(F.data == "remind_ok")
async def remind_confirm(callback: CallbackQuery):
    """Клиент нажал «Приду»."""
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Спасибо! Ждём вас 💖"
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Отлично, ждём вас!")