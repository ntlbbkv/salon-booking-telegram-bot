import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from database.db import init_db
from handlers import start, booking, my_bookings, admin
from reminders import router as reminders_router, reminder_loop

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()
dp.include_router(admin.router)
dp.include_router(booking.router)
dp.include_router(my_bookings.router)
dp.include_router(reminders_router)
dp.include_router(start.router)


async def main():
    await init_db()
    # Запускаем напоминания в фоне
    reminder_task = asyncio.create_task(reminder_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()  # останавливаем фоновый цикл
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")