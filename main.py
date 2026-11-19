"""Entry point: builds the Dispatcher, includes routers, starts polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher


async def main() -> None:
    from config import load_settings

    settings = load_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set (see .env.example)")
    logging.basicConfig(level=logging.INFO)
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
