from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import SALON_NAME, SALON_ADDRESS, SALON_PHONE, SALON_HOURS, SERVICES
from keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Здравствуйте, {message.from_user.first_name}! 💖\n"
        f"Добро пожаловать в {SALON_NAME}.\n"
        "Выберите действие в меню ниже 👇",
        reply_markup=main_menu(),
    )


@router.message(F.text == "💅 Услуги")
async def show_services(message: Message, state: FSMContext):
    await state.clear()
    lines = ["💅 Наши услуги:\n"]
    for s in SERVICES:
        lines.append(f"• {s['name']} — {s['price']} ₽ ({s['duration']} мин)")
    await message.answer("\n".join(lines))


@router.message(F.text == "📍 Контакты")
async def show_contacts(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"📍 Адрес: {SALON_ADDRESS}\n"
        f"📞 Телефон: {SALON_PHONE}\n"
        f"🕒 Часы работы: {SALON_HOURS}"
    )