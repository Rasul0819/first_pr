"""Admin panel: statistics, user list and manual plan management.

Access is limited to IDs listed in ADMIN_IDS. `/setplan` is the hook that a
future payment integration will call (via Database.set_plan) to grant
paid subscriptions.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import escape

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import Settings
from database import PLANS, Database
from keyboards.admin import admin_panel
from utils import fmt_money


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, settings: Settings) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id in settings.admin_ids


router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def stats_text(db: Database) -> str:
    s = await db.stats()
    return "\n".join([
        "📈 <b>Statistics</b>",
        f"Users: <b>{s['users']}</b> (paid: {s['paid_users']})",
        f"Active this month: <b>{s['active_month']}</b>",
        f"Transactions: <b>{s['transactions']}</b>",
        f"Total income logged: {fmt_money(s['income_cents'])}",
        f"Total expenses logged: {fmt_money(s['expense_cents'])}",
    ])


async def users_text(db: Database) -> str:
    rows = await db.recent_users(10)
    if not rows:
        return "No users yet."
    lines = ["👥 <b>Recent users</b>"]
    for r in rows:
        who = f"@{escape(r['username'])}" if r["username"] else escape(r["full_name"] or "—")
        lines.append(f"<code>{r['user_id']}</code> {who} · {r['plan']}")
    return "\n".join(lines)


@router.message(Command("admin"))
async def admin_cmd(message: Message) -> None:
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_panel())


@router.message(Command("stats"))
async def stats_cmd(message: Message, db: Database) -> None:
    await message.answer(await stats_text(db))


@router.callback_query(F.data == "adm:stats")
async def stats_cb(call: CallbackQuery, db: Database) -> None:
    await call.message.answer(await stats_text(db))
    await call.answer()


@router.callback_query(F.data == "adm:users")
async def users_cb(call: CallbackQuery, db: Database) -> None:
    await call.message.answer(await users_text(db))
    await call.answer()


@router.message(Command("setplan"))
async def setplan_cmd(message: Message, db: Database, command: CommandObject) -> None:
    """/setplan <user_id> <plan> [days]  — e.g. /setplan 123456 pro 30"""
    usage = f"Usage: <code>/setplan &lt;user_id&gt; &lt;{'|'.join(PLANS)}&gt; [days]</code>"
    parts = (command.args or "").split()
    try:
        if not 2 <= len(parts) <= 3:
            raise ValueError
        uid, plan = int(parts[0]), parts[1].lower()
        days = int(parts[2]) if len(parts) == 3 else None
        if plan not in PLANS or (days is not None and not 1 <= days <= 3650):
            raise ValueError
    except ValueError:
        await message.answer(usage)
        return
    expires = (date.today() + timedelta(days=days)).isoformat() if days and plan != "free" else None
    if not await db.set_plan(uid, plan, expires):
        await message.answer(f"User <code>{uid}</code> not found.")
        return
    until = f" until {expires}" if expires else ""
    await message.answer(f"✅ User <code>{uid}</code> is now <b>{plan}</b>{until}.")
