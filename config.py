import os

from dotenv import load_dotenv

load_dotenv()  # читаем файл .env

SALON_NAME = "Beauty Studio"
SALON_ADDRESS = "г. Москва, ул. Примерная, 10"
SALON_PHONE = "+7 (900) 000-00-00"
SALON_HOURS = "Ежедневно с 10:00 до 21:00"

# Услуги: название, цена в рублях, длительность в минутах
SERVICES = [
    {"name": "Маникюр", "price": 1500, "duration": 60},
    {"name": "Педикюр", "price": 2000, "duration": 90},
    {"name": "Стрижка", "price": 1800, "duration": 60},
    {"name": "Окрашивание", "price": 4500, "duration": 150},
    {"name": "Макияж", "price": 2500, "duration": 60},
]

# Время начала сеансов: каждый час с 10:00 до 20:00
SLOTS = [f"{hour:02d}:00" for hour in range(10, 21)]

# На сколько дней вперёд можно записаться
BOOKING_DAYS_AHEAD = 60

# Telegram ID администратора (из файла .env). 0 = уведомления выключены
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# За сколько часов до визита отправлять напоминание
REMINDER_HOURS = 24

# Как часто бот проверяет, пора ли отправлять напоминания (в секундах)
REMINDER_CHECK_SECONDS = 60