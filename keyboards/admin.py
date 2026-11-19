"""Admin panel keyboards."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📈 Stats", callback_data="adm:stats")
    b.button(text="👥 Recent users", callback_data="adm:users")
    b.adjust(2)
    return b.as_markup()
