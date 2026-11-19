"""Admin panel keyboards."""
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales import kaa as T


def admin_panel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_ADMIN_STATS, callback_data="adm:stats")
    b.button(text=T.BTN_ADMIN_USERS, callback_data="adm:users")
    b.adjust(2)
    return b.as_markup()
