import asyncio
import logging
import sys
from pathlib import Path
from aiogram import types


from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import settings
from middlewares.database import DataBaseSessionMiddleware
from middlewares.rate_limiter import RateLimiterMiddleware
from handlers import start, admin, admin_promos, admin_channels, admin_broadcast, admin_users, admin_gift, admin_balance, admin_activity, admin_stars, system_stats, gift_payout, ton_requests, gift_promos, transactions, admin_user, stars_payment, lottery

# sys.path.append(str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=settings.bot_token,
    )
    dp = Dispatcher()

    # Middleware для сессии
    dp.update.middleware(DataBaseSessionMiddleware())
    dp.update.middleware(RateLimiterMiddleware(rate=30, time_period=1))

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(admin_promos.router)
    dp.include_router(admin_channels.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_user.router)
    dp.include_router(gift_promos.router)
    dp.include_router(admin_gift.router)
    dp.include_router(admin_balance.router)
    dp.include_router(admin_stars.router)
    dp.include_router(system_stats.router)
    dp.include_router(gift_payout.router)
    dp.include_router(ton_requests.router)
    dp.include_router(transactions.router)
    dp.include_router(stars_payment.router)
    dp.include_router(admin_activity.router)
    dp.include_router(lottery.router)







    logger.info("🚀 Бот запускается...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("🛑 Остановка бота...")
        await bot.session.close()
        logger.info("✅ Сессия закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⚠️ Бот был остановлен вручную")


#
# import asyncio
# import logging
# import sys
# from pathlib import Path
# from aiogram import types
#
# from aiogram import Bot, Dispatcher
# from aiogram.client.default import DefaultBotProperties
#
#
# # Абсолютные импорты вместо относительных
# sys.path.append(str(Path(__file__).resolve().parent.parent))
#
# from bot.config import settings
# from bot.middlewares.db import DataBaseSessionMiddleware
# from bot.middlewares.rate_limiter import RateLimiterMiddleware
#
#
# from bot.handlers import start, admin, admin_promos, admin_channels, admin_broadcast, admin_users, admin_gift, admin_balance, admin_activity, admin_stars, system_stats, business_debug, gift_payout, ton_requests, gift_promos, transactions, admin_user, stars_payment, lottery
#
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#     handlers=[logging.StreamHandler(sys.stdout)],
# )
# logger = logging.getLogger(__name__)
#
#
# async def main():
#     bot = Bot(
#         token=settings.bot_token,
#         # default=DefaultBotProperties(parse_mode="HTML"),
#     )
#     dp = Dispatcher()
#
#     # Middleware для сессии
#     dp.update.middleware(DataBaseSessionMiddleware())
#     dp.update.middleware(RateLimiterMiddleware(rate=25, time_period=1))
#
#     # Роутеры
#     dp.include_router(start.router)
#     dp.include_router(admin.router)
#     dp.include_router(admin_promos.router)
#     dp.include_router(admin_channels.router)
#     dp.include_router(admin_broadcast.router)
#     dp.include_router(admin_users.router)
#     dp.include_router(admin_user.router)
#     dp.include_router(gift_promos.router)
#     dp.include_router(admin_gift.router)
#     dp.include_router(admin_balance.router)
#     dp.include_router(admin_stars.router)
#     dp.include_router(system_stats.router)
#     dp.include_router(business_debug.router)
#     dp.include_router(gift_payout.router)
#     dp.include_router(ton_requests.router)
#     dp.include_router(transactions.router)
#     dp.include_router(stars_payment.router)
#     dp.include_router(admin_activity.router)
#     dp.include_router(lottery.router)
#
#     logger.info("🚀 Бот запускается...")
#
#     try:
#         await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
#     finally:
#         logger.info("🛑 Остановка бота...")
#         await bot.session.close()
#         logger.info("✅ Сессия закрыта")
#
#
# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except (KeyboardInterrupt, SystemExit):
#         logger.info("⚠️ Бот был остановлен вручную")
#
