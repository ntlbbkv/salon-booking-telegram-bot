from aiogram.exceptions import TelegramAPIError

from config import ADMIN_ID


async def notify_admin(bot, text: str) -> None:
    """Отправляет сообщение администратору. Если не вышло, бот не падает."""
    if not ADMIN_ID:
        return
    try:
        await bot.send_message(ADMIN_ID, text)
    except TelegramAPIError:
        pass  # например, админ ещё не нажал Start у бота