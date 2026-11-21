import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOOKING_DAYS_AHEAD
from keyboards.inline import nav_buttons

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _noop(text: str = " ") -> InlineKeyboardButton:
    """Кнопка-пустышка: при нажатии ничего не происходит."""
    return InlineKeyboardButton(text=text, callback_data="noop")


def calendar_kb(year: int, month: int) -> InlineKeyboardMarkup:
    today = date.today()
    last_day = today + timedelta(days=BOOKING_DAYS_AHEAD)

    # Можно ли листать назад / вперёд
    has_prev = (year, month) > (today.year, today.month)
    has_next = (year, month) < (last_day.year, last_day.month)

    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    rows = []

    # Строка 1: стрелки и название месяца
    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"calnav:{prev_y}-{prev_m:02d}")
        if has_prev else _noop(),
        _noop(f"{MONTHS[month - 1]} {year}"),
        InlineKeyboardButton(text="▶️", callback_data=f"calnav:{next_y}-{next_m:02d}")
        if has_next else _noop(),
    ])

    # Строка 2: дни недели
    rows.append([_noop(name) for name in WEEKDAYS])

    # Строки с числами. monthcalendar отдаёт недели, пустые клетки = 0
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(_noop())
                continue
            current = date(year, month, day)
            if current < today or current > last_day:
                row.append(_noop("·"))  # недоступный день
            else:
                label = f"[{day}]" if current == today else str(day)  # сегодня в скобках
                row.append(
                    InlineKeyboardButton(
                        text=label, callback_data=f"date:{current.isoformat()}"
                    )
                )
        rows.append(row)

    rows.append(nav_buttons())
    return InlineKeyboardMarkup(inline_keyboard=rows)