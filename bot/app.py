import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from .config import settings
from .middlewares.db import DataBaseSessionMiddleware
from .handlers import start, admin, admin_promos


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    # Middleware для сессии
    # dp.message.middleware(DataBaseSessionMiddleware())
    dp.update.middleware(DataBaseSessionMiddleware())

    # Роутеры

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(admin_promos.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
