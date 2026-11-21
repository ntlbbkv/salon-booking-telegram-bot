import re
from datetime import date, datetime

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import SERVICES
from database.db import add_booking, get_busy_times
from keyboards.date_picker import calendar_kb
from keyboards.inline import services_kb, times_kb, free_slots, text_step_kb
from keyboards.main_menu import main_menu, MENU_BUTTONS
from utils import notify_admin

router = Router()


class Booking(StatesGroup):
    """Шаги записи."""
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()


# ---------- Вспомогательные функции ----------

def pretty_date(date_str: str) -> str:
    """2026-11-21 -> 21.11.2026"""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")


FIELDS = [("service", "Услуга"), ("date", "Дата"), ("time", "Время"), ("name", "Имя")]


def summary(data: dict, step: str) -> str:
    """Что уже выбрано: только то, что идёт ДО текущего шага."""
    lines = []
    for key, title in FIELDS:
        if key == step:
            break
        value = data.get(key)
        if value:
            lines.append(f"{title}: {pretty_date(value) if key == 'date' else value}")
    return "\n".join(lines)


def with_summary(data: dict, step: str, text: str) -> str:
    done = summary(data, step)
    return f"{done}\n\n{text}" if done else text


async def show(bot, chat_id: int, state: FSMContext, text: str, kb=None) -> None:
    """Редактирует единственное сообщение «мастера записи»."""
    data = await state.get_data()
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=data["msg_id"], text=text, reply_markup=kb
        )
    except TelegramBadRequest:
        pass  # например, текст не изменился. Это не ошибка


async def delete_quietly(message: Message) -> None:
    """Удаляет сообщение пользователя, чтобы чат был чистым."""
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


# ---------- Экраны (шаги записи) ----------

async def screen_service(bot, chat_id, state):
    await state.set_state(Booking.service)
    await show(bot, chat_id, state, "Выберите услугу:", services_kb())


async def screen_date(bot, chat_id, state, year=None, month=None):
    await state.set_state(Booking.date)
    data = await state.get_data()
    if year is None:
        # Открываем месяц ранее выбранной даты, а если даты нет, то текущий
        base = date.fromisoformat(data["date"]) if data.get("date") else date.today()
        year, month = base.year, base.month
    text = with_summary(data, "date", "Выберите дату:")
    await show(bot, chat_id, state, text, calendar_kb(year, month))


async def screen_time(bot, chat_id, state):
    await state.set_state(Booking.time)
    data = await state.get_data()
    busy = await get_busy_times(data["date"])
    slots = free_slots(data["date"], busy)
    text = with_summary(data, "time", "Выберите время:")
    await show(bot, chat_id, state, text, times_kb(slots))


async def screen_name(bot, chat_id, state, error=None):
    await state.set_state(Booking.name)
    data = await state.get_data()
    text = with_summary(data, "name", "Как к вам обращаться? Напишите ваше имя.")
    if error:
        text += f"\n\n⚠️ {error}"
    await show(bot, chat_id, state, text, text_step_kb())


async def screen_phone(bot, chat_id, state, error=None):
    await state.set_state(Booking.phone)
    data = await state.get_data()
    text = with_summary(
        data, "phone", "Напишите номер телефона для связи, например +7 900 123-45-67"
    )
    if error:
        text += f"\n\n⚠️ {error}"
    await show(bot, chat_id, state, text, text_step_kb())


# ---------- Запуск и отмена ----------

@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    sent = await message.answer("Выберите услугу:", reply_markup=services_kb())
    await state.set_state(Booking.service)
    await state.update_data(msg_id=sent.message_id)  # запоминаем, какое сообщение редактировать


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Запись отменена.", reply_markup=main_menu())


@router.callback_query(StateFilter(Booking), F.data == "cancel")
async def cancel_button(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.answer()


# ---------- Кнопка «Назад» ----------

@router.callback_query(StateFilter(Booking), F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    bot, chat_id = callback.bot, callback.message.chat.id

    if current == Booking.date.state:
        await screen_service(bot, chat_id, state)
    elif current == Booking.time.state:
        await screen_date(bot, chat_id, state)
    elif current == Booking.name.state:
        await screen_time(bot, chat_id, state)
    elif current == Booking.phone.state:
        await screen_name(bot, chat_id, state)
    await callback.answer()


# ---------- Шаги с кнопками ----------

@router.callback_query(Booking.service, F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split(":")[1])
    await state.update_data(service=SERVICES[index]["name"])
    await screen_date(callback.bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(Booking.date, F.data.startswith("calnav:"))
async def calendar_nav(callback: CallbackQuery, state: FSMContext):
    # "calnav:2026-12" -> год 2026, месяц 12
    year, month = map(int, callback.data.split(":")[1].split("-"))
    await screen_date(callback.bot, callback.message.chat.id, state, year, month)
    await callback.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":", 1)[1]
    busy = await get_busy_times(date_str)
    if not free_slots(date_str, busy):
        await callback.answer("На этот день свободных мест нет", show_alert=True)
        return
    await state.update_data(date=date_str)
    await screen_time(callback.bot, callback.message.chat.id, state)
    await callback.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time = callback.data.split(":", 1)[1]  # "time:10:00" -> "10:00"
    await state.update_data(time=time)
    await screen_name(callback.bot, callback.message.chat.id, state)
    await callback.answer()


# ---------- Шаги с вводом текста ----------
# Фильтры ~F.text.in_(MENU_BUTTONS) и ~F.text.startswith("/") означают:
# «не реагируй, если человек нажал кнопку меню или написал команду».

@router.message(Booking.name, F.text, ~F.text.in_(MENU_BUTTONS), ~F.text.startswith("/"))
async def get_name(message: Message, state: FSMContext):
    bot, chat_id = message.bot, message.chat.id
    name = message.text.strip()
    await delete_quietly(message)

    if len(name) < 2 or len(name) > 50:
        await screen_name(bot, chat_id, state, error="Имя должно быть от 2 до 50 символов.")
        return

    await state.update_data(name=name)
    await screen_phone(bot, chat_id, state)


@router.message(Booking.phone, F.text, ~F.text.in_(MENU_BUTTONS), ~F.text.startswith("/"))
async def get_phone(message: Message, state: FSMContext):
    bot, chat_id = message.bot, message.chat.id
    phone = message.text.strip()
    await delete_quietly(message)

    digits = re.sub(r"\D", "", phone)  # оставляем только цифры
    if not 10 <= len(digits) <= 15:
        await screen_phone(bot, chat_id, state, error="Похоже, номер введён неверно. Попробуйте ещё раз.")
        return

    data = await state.get_data()

    # Проверяем ещё раз: вдруг это время успели занять
    busy = await get_busy_times(data["date"])
    if data["time"] in busy:
        await show(
            bot, chat_id, state,
            "К сожалению, это время только что заняли 😔\n"
            "Нажмите «📅 Записаться» и выберите другое.",
        )
        await state.clear()
        return

    # 1) Сначала сохраняем запись: так появляется booking_id
    booking_id = await add_booking(
        user_id=message.from_user.id,
        service=data["service"],
        date=data["date"],
        time=data["time"],
        name=data["name"],
        phone=phone,
    )

    # 2) Потом сообщаем администратору
    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "username не указан"
    )
    await notify_admin(
        bot,
        f"🔔 Новая запись #{booking_id}\n\n"
        f"Услуга: {data['service']}\n"
        f"Дата: {pretty_date(data['date'])}\n"
        f"Время: {data['time']}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {phone}\n"
        f"Telegram: {username}",
    )

    # 3) И показываем клиенту подтверждение
    await show(
        bot, chat_id, state,
        "✅ Вы записаны!\n\n"
        f"Услуга: {data['service']}\n"
        f"Дата: {pretty_date(data['date'])}\n"
        f"Время: {data['time']}\n"
        f"Имя: {data['name']}\n\n"
        "Ждём вас в салоне 💖",
    )
    await state.clear()


# ---------- Служебные кнопки (должны стоять в самом конце файла) ----------

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    """Нажатие на пустые клетки календаря: просто «гасим» крутилку на кнопке."""
    await callback.answer()


@router.callback_query(F.data.regexp(r"^(service:|date:|time:|calnav:|back$|cancel$)"))
async def stale_button(callback: CallbackQuery):
    """Кнопки из старых сообщений, когда запись уже закончена или прервана."""
    await callback.answer(
        "Эта кнопка устарела. Нажмите «📅 Записаться» и начните заново.",
        show_alert=True,
    )