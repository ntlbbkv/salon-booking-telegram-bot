from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Тексты кнопок меню. Если поменяете текст кнопки, поменяйте и здесь
MENU_BUTTONS = ["💅 Услуги", "📅 Записаться", "📋 Мои записи", "📍 Контакты"]


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💅 Услуги"), KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="📋 Мои записи"), KeyboardButton(text="📍 Контакты")],
        ],
        resize_keyboard=True,
    )