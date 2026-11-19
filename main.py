"""Entry point: builds the Dispatcher, includes routers, starts polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Settings, load_settings
from database import Database
from handlers import user


def build_dispatcher(db: Database, settings: Settings) -> Dispatcher:
    dp = Dispatcher()
    dp["db"] = db            # injected into handlers by parameter name
    dp["settings"] = settings
    dp.include_router(user.router)
    return dp


async def main() -> None:
    settings = load_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set (see .env.example)")
    logging.basicConfig(level=logging.INFO)
    db = Database(settings.db_path)
    await db.connect()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await build_dispatcher(db, settings).start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
