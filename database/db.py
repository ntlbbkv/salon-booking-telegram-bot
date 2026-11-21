from datetime import datetime, timedelta

import aiosqlite

from config import REMINDER_HOURS

DB_PATH = "salon.db"


async def init_db():
    """Создаёт таблицу записей, если её ещё нет, и добавляет новые столбцы."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                reminded INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Миграция: если база создана раньше и столбца reminded нет, добавляем его
        async with db.execute("PRAGMA table_info(bookings)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
        if "reminded" not in columns:
            await db.execute(
                "ALTER TABLE bookings ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0"
            )

        await db.commit()


async def add_booking(user_id, service, date, time, name, phone) -> int:
    """Сохраняет новую запись и возвращает её номер."""
    # Если до визита уже меньше REMINDER_HOURS часов, напоминание не нужно
    visit = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    reminded = 1 if visit - datetime.now() <= timedelta(hours=REMINDER_HOURS) else 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bookings (user_id, service, date, time, name, phone, reminded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, service, date, time, name, phone, reminded),
        )
        await db.commit()
        return cursor.lastrowid


async def get_busy_times(date):
    """Возвращает список занятого времени на выбранную дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT time FROM bookings WHERE date = ?", (date,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_user_bookings(user_id, today):
    """Будущие записи одного человека, от ближайших к дальним."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE user_id = ? AND date >= ? "
            "ORDER BY date, time",
            (user_id, today),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_booking(booking_id):
    """Одна запись по номеру (или None, если такой нет)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_booking(booking_id, user_id) -> bool:
    """Удаляет запись. Условие user_id не даст удалить чужую запись."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM bookings WHERE id = ? AND user_id = ?",
            (booking_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_bookings_by_date(date_str):
    """Все записи на один день (для администратора), по времени."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE date = ? ORDER BY time",
            (date_str,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_upcoming_bookings(today, limit=30):
    """Ближайшие записи начиная с сегодня (не больше limit штук)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE date >= ? ORDER BY date, time LIMIT ?",
            (today, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_pending_reminders(today):
    """Записи с сегодняшнего дня, по которым напоминание ещё не отправляли."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bookings WHERE date >= ? AND reminded = 0 "
            "ORDER BY date, time",
            (today,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def mark_reminded(booking_id):
    """Отмечает, что напоминание по этой записи отправлено."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,)
        )
        await db.commit()