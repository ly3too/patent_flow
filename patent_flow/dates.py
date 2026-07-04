"""Date-math helpers used for deadline calculations. No external dependency
(avoids adding python-dateutil just for month arithmetic)."""
import calendar
from datetime import date


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)
