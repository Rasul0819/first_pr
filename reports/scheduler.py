"""End-of-month delivery: on the 1st of each month send last month's report."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from aiogram import Bot
from aiogram.types import BufferedInputFile

from database import Database
from reports.monthly import generate_monthly_report
from utils import month_title, previous_month

log = logging.getLogger(__name__)
SEND_HOUR = 9  # local server time


async def send_monthly_reports(bot: Bot, db: Database, today: date | None = None) -> int:
    """Send the previous month's report to every user who had activity. Returns count sent."""
    year, month = previous_month(today)
    sent = 0
    for uid in await db.user_ids():
        if not await db.month_transactions(uid, year, month):
            continue
        try:
            name, data = await generate_monthly_report(db, uid, year, month)
            await bot.send_document(uid, BufferedInputFile(data, name),
                                    caption=f"📊 Your {month_title(year, month)} report")
            sent += 1
        except Exception:  # one blocked user must not stop the rest
            log.exception("failed to send report to %s", uid)
        await asyncio.sleep(0.05)  # stay under Telegram flood limits
    return sent


def seconds_until_next_run(now: datetime) -> float:
    nxt = now.replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def monthly_report_loop(bot: Bot, db: Database) -> None:
    while True:
        await asyncio.sleep(seconds_until_next_run(datetime.now()))
        if date.today().day == 1:
            n = await send_monthly_reports(bot, db)
            log.info("monthly reports sent: %d", n)
