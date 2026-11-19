"""Keyboards for regular users."""
from __future__ import annotations

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Transaction
from utils import fmt_money

BTN_EXPENSE = "➖ Expense"
BTN_INCOME = "➕ Income"
BTN_REPORT = "📊 Report"
BTN_HISTORY = "🕘 History"

EXPENSE_CATEGORIES = ["🍔 Food", "🚌 Transport", "🏠 Housing", "🛍 Shopping",
                      "💊 Health", "🎬 Fun", "📚 Education", "📦 Other"]
INCOME_SOURCES = ["💼 Salary", "🧾 Freelance", "🎁 Gift", "📈 Investments", "📦 Other"]


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
    b.button(text="✏️ Custom…", callback_data="cat:custom")
    b.button(text="✖️ Cancel", callback_data="cancel")
    b.adjust(2)
    return b.as_markup()


def skip_note_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Skip note", callback_data="note:skip")
    b.button(text="✖️ Cancel", callback_data="cancel")
    b.adjust(2)
    return b.as_markup()


def report_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="This month", callback_data="report:current")
    b.button(text="Last month", callback_data="report:previous")
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
