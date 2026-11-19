"""Keyboards for regular users."""
from __future__ import annotations

from aiogram.types import (InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Transaction
from locales import kaa as T
from utils import fmt_money

# Re-exported so handlers/tests match menu text without importing locales directly.
BTN_EXPENSE, BTN_INCOME = T.BTN_EXPENSE, T.BTN_INCOME
BTN_REPORT, BTN_HISTORY = T.BTN_REPORT, T.BTN_HISTORY
EXPENSE_CATEGORIES, INCOME_SOURCES = T.EXPENSE_CATEGORIES, T.INCOME_SOURCES


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_EXPENSE), KeyboardButton(text=BTN_INCOME)],
                  [KeyboardButton(text=BTN_REPORT), KeyboardButton(text=BTN_HISTORY)]],
        resize_keyboard=True,
    )


def category_kb(options: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, name in enumerate(options):
        b.button(text=name, callback_data=f"cat:{i}")
    b.button(text=T.BTN_CUSTOM, callback_data="cat:custom")
    b.button(text=T.BTN_CANCEL, callback_data="cancel")
    b.adjust(2)
    return b.as_markup()


def skip_note_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_SKIP_NOTE, callback_data="note:skip")
    b.button(text=T.BTN_CANCEL, callback_data="cancel")
    b.adjust(2)
    return b.as_markup()


def report_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_REPORT_CURRENT, callback_data="report:current")
    b.button(text=T.BTN_REPORT_PREVIOUS, callback_data="report:previous")
    b.adjust(2)
    return b.as_markup()


def history_kb(txs: list[Transaction]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in txs:
        sign = "-" if t.kind == "expense" else "+"
        b.button(text=f"🗑 {t.tx_date[5:]} {sign}{fmt_money(t.amount_cents)} {t.category}"[:60],
                 callback_data=f"del:{t.id}")
    b.adjust(1)
    return b.as_markup()
