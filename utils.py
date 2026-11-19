"""Small shared helpers."""
from __future__ import annotations

from datetime import date

from locales import kaa as T


def fmt_money(cents: int) -> str:
    """12345 -> '123.45', 123456 -> '1 234.56' (negative aware)."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}".replace(",", " ") + f".{frac:02d}"


def current_year_month(today: date | None = None) -> tuple[int, int]:
    t = today or date.today()
    return t.year, t.month


def previous_month(today: date | None = None) -> tuple[int, int]:
    t = today or date.today()
    return (t.year - 1, 12) if t.month == 1 else (t.year, t.month - 1)


def month_title(year: int, month: int) -> str:
    return T.MONTH_TITLE.format(year=year, month=T.MONTHS[month - 1])
