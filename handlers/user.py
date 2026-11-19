"""User-facing flows: logging expenses/income, history, deleting entries."""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import EXPENSE, INCOME, Database, to_cents
from keyboards import user as kb
from utils import fmt_money

router = Router(name="user")

MAX_CATEGORY = 30
MAX_NOTE = 200


class AddTx(StatesGroup):
    amount = State()
    category = State()
    custom_category = State()
    note = State()


def _options(kind: str) -> list[str]:
    return kb.EXPENSE_CATEGORIES if kind == EXPENSE else kb.INCOME_SOURCES


def _label(kind: str) -> str:
    return "category" if kind == EXPENSE else "source"


# --------------------------------------------------------------- basics
@router.message(CommandStart())
async def start(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    u = message.from_user
    await db.upsert_user(u.id, u.username, u.full_name)
    await message.answer(
        "👋 <b>Expense &amp; Income Tracker</b>\n\n"
        "Log what you spend and earn, then get a monthly Excel dashboard.\n"
        "Use the menu below. /cancel stops any action.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("cancel"), StateFilter("*"))
async def cancel_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled.", reply_markup=kb.main_menu())


@router.callback_query(F.data == "cancel", StateFilter("*"))
async def cancel_cb(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("Cancelled.")
    await call.answer()


# --------------------------------------------------------------- add flow
async def _begin(message: Message, state: FSMContext, db: Database, kind: str) -> None:
    u = message.from_user
    await db.upsert_user(u.id, u.username, u.full_name)
    await state.clear()
    await state.set_state(AddTx.amount)
    await state.update_data(kind=kind)
    what = "expense" if kind == EXPENSE else "income"
    await message.answer(f"Enter the {what} amount (e.g. <code>12.50</code>):")


@router.message(F.text == kb.BTN_EXPENSE, StateFilter("*"))
async def new_expense(message: Message, state: FSMContext, db: Database) -> None:
    await _begin(message, state, db, EXPENSE)


@router.message(F.text == kb.BTN_INCOME, StateFilter("*"))
async def new_income(message: Message, state: FSMContext, db: Database) -> None:
    await _begin(message, state, db, INCOME)


@router.message(AddTx.amount, F.text)
async def got_amount(message: Message, state: FSMContext) -> None:
    try:
        cents = to_cents(message.text)
    except ValueError:
        await message.answer("❗ Please send a positive number with up to 2 decimals, e.g. <code>12.50</code>.")
        return
    data = await state.get_data()
    await state.update_data(cents=cents)
    await state.set_state(AddTx.category)
    await message.answer(f"Amount: <b>{fmt_money(cents)}</b>\nChoose a {_label(data['kind'])}:",
                         reply_markup=kb.category_kb(_options(data["kind"])))


async def _after_category(target: Message, state: FSMContext, db: Database, user_id: int, category: str) -> None:
    data = await state.get_data()
    await state.update_data(category=category)
    if data["kind"] == EXPENSE:
        await state.set_state(AddTx.note)
        await target.answer(f"Category: <b>{escape(category)}</b>\nAdd a note (or skip):",
                            reply_markup=kb.skip_note_kb())
    else:
        await _save(target, state, db, user_id, note="")


@router.callback_query(AddTx.category, F.data == "cat:custom")
async def custom_cat(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(AddTx.custom_category)
    await call.message.edit_text(f"Type your {_label(data['kind'])} name (max {MAX_CATEGORY} chars):")
    await call.answer()


@router.callback_query(AddTx.category, F.data.regexp(r"^cat:\d+$"))
async def pick_cat(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    opts = _options(data["kind"])
    idx = int(call.data.split(":")[1])
    if idx >= len(opts):
        await call.answer("Unknown option", show_alert=True)
        return
    await call.message.edit_reply_markup(reply_markup=None)
    await _after_category(call.message, state, db, call.from_user.id, opts[idx])
    await call.answer()


@router.message(AddTx.custom_category, F.text)
async def got_custom_cat(message: Message, state: FSMContext, db: Database) -> None:
    name = message.text.strip()
    if not name or len(name) > MAX_CATEGORY:
        await message.answer(f"❗ Name must be 1–{MAX_CATEGORY} characters.")
        return
    await _after_category(message, state, db, message.from_user.id, name)


@router.callback_query(AddTx.note, F.data == "note:skip")
async def skip_note(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    await call.message.edit_reply_markup(reply_markup=None)
    await _save(call.message, state, db, call.from_user.id, note="")
    await call.answer()


@router.message(AddTx.note, F.text)
async def got_note(message: Message, state: FSMContext, db: Database) -> None:
    note = message.text.strip()
    if len(note) > MAX_NOTE:
        await message.answer(f"❗ Note is too long (max {MAX_NOTE} chars).")
        return
    await _save(message, state, db, message.from_user.id, note=note)


async def _save(target: Message, state: FSMContext, db: Database, user_id: int, note: str) -> None:
    data = await state.get_data()
    await state.clear()
    await db.add_transaction(user_id, data["kind"], data["cents"], data["category"], note)
    sign = "−" if data["kind"] == EXPENSE else "+"
    text = f"✅ Saved: <b>{sign}{fmt_money(data['cents'])}</b> · {escape(data['category'])}"
    if note:
        text += f"\n📝 {escape(note)}"
    await target.answer(text, reply_markup=kb.main_menu())


# --------------------------------------------------------------- history
def _history_text(txs) -> str:
    if not txs:
        return "No entries yet. Add one with ➖ Expense or ➕ Income."
    lines = ["🕘 <b>Last entries</b> (tap to delete):"]
    for t in txs:
        sign = "−" if t.kind == EXPENSE else "+"
        note = f" — {escape(t.note)}" if t.note else ""
        lines.append(f"{t.tx_date} {sign}{fmt_money(t.amount_cents)} {escape(t.category)}{note}")
    return "\n".join(lines)


@router.message(F.text == kb.BTN_HISTORY, StateFilter("*"))
@router.message(Command("history"), StateFilter("*"))
async def history(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    txs = await db.recent(message.from_user.id, 10)
    await message.answer(_history_text(txs), reply_markup=kb.history_kb(txs) if txs else None)


@router.callback_query(F.data.regexp(r"^del:\d+$"))
async def delete_tx(call: CallbackQuery, db: Database) -> None:
    ok = await db.delete_transaction(call.from_user.id, int(call.data.split(":")[1]))
    txs = await db.recent(call.from_user.id, 10)
    await call.message.edit_text(_history_text(txs), reply_markup=kb.history_kb(txs) if txs else None)
    await call.answer("Deleted" if ok else "Already deleted")
