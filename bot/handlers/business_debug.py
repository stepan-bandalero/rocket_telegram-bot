from __future__ import annotations

import json
import logging
import redis.asyncio as aioredis
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import BusinessConnection
from aiogram.methods import GetBusinessAccountGifts, GetAvailableGifts, GetBusinessConnection, SendGift

logger = logging.getLogger(__name__)

router = Router(name="business_debug")

# Настроим Redis клиент (rocket-top.app:6379)
redis = aioredis.Redis(host="rocket-app.top", port=6379, decode_responses=True)


async def get_conn_id_from_message_or_redis(message: types.Message) -> str | None:
    """Пробуем взять business_connection_id из апдейта или Redis"""
    if message.business_connection_id:
        return message.business_connection_id
    conn_id = await redis.get("business_connection_id")
    if conn_id:
        logger.info("📦 business_connection_id взят из Redis: %s", conn_id)
    return conn_id


# Ловим апдейты business_connection (например, при подключении/отключении)
@router.business_connection()
async def handle_business_connection(bc: BusinessConnection):
    logger.info("🔗 BusinessConnection event:\n%s", json.dumps(bc.model_dump(), indent=2, ensure_ascii=False))
    await redis.set("business_connection_id", bc.id)
    logger.info("💾 business_connection_id сохранён в Redis: %s", bc.id)


# Команда: проверить текущее business_connection_id
@router.message(Command("my_business_conn"))
async def cmd_my_business_conn(message: types.Message):
    conn_id = await get_conn_id_from_message_or_redis(message)
    if conn_id:
        logger.info("📎 business_connection_id: %s", conn_id)
    else:
        logger.info("❌ business_connection_id не найден (ни в апдейте, ни в Redis)")


# Команда: получить полное описание business_connection
@router.message(Command("debug_business_conn"))
async def cmd_debug_business_conn(message: types.Message, bot: Bot):
    conn_id = await get_conn_id_from_message_or_redis(message)
    if not conn_id:
        logger.info("❌ business_connection_id не найден")
        return

    try:
        resp = await bot(GetBusinessConnection(business_connection_id=conn_id))
        logger.info("📑 GetBusinessConnection response:\n%s",
                    json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("❌ Ошибка получения business connection: %s", e)


# Команда: вытащить все подарки бизнес-аккаунта
@router.message(Command("debug_business_gifts"))
async def cmd_debug_business_gifts(message: types.Message, bot: Bot):
    conn_id = await get_conn_id_from_message_or_redis(message)
    if not conn_id:
        logger.info("❌ business_connection_id не найден")
        return

    try:
        resp = await bot(GetBusinessAccountGifts(
            business_connection_id=conn_id,
            limit=100,
            offset="0"
        ))
        logger.info("🎁 GetBusinessAccountGifts response:\n%s",
                    json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("❌ Ошибка получения подарков бизнес-аккаунта: %s", e)


# Команда: посмотреть список доступных подарков
@router.message(Command("debug_available_gifts"))
async def cmd_debug_available_gifts(message: types.Message, bot: Bot):
    try:
        resp = await bot(GetAvailableGifts())
        logger.info("🎁 GetAvailableGifts response:\n%s", json.dumps(resp.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("❌ Ошибка получения доступных подарков: %s", e)


# Обработчик для отправки подарка пользователю
@router.message(Command("send_gift"))
async def cmd_send_gift(message: types.Message, bot: Bot):
    """
    Формат команды: /send_gift <user_id> <gift_id>
    Пример: /send_gift 123456789 gift_abc123
    """
    try:
        # Парсим аргументы команды
        args = message.text.split()
        if len(args) != 3:
            logger.info("❌ Неправильный формат команды. Используйте: /send_gift <user_id> <gift_id>")
            return

        user_id = int(args[1])
        gift_id = args[2]

        # Получаем business_connection_id
        conn_id = await get_conn_id_from_message_or_redis(message)
        if not conn_id:
            logger.info("❌ business_connection_id не найден")
            return

        # Отправляем подарок
        logger.info(f"🎁 Отправка подарка: user_id={user_id}, gift_id={gift_id}, business_connection_id={conn_id}")

        result = await bot(SendGift(
            business_connection_id=conn_id,
            user_id=user_id,
            gift_id=gift_id
        ))

        logger.info("✅ Подарок успешно отправлен! Response:\n%s",
                    json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

    except ValueError:
        logger.info("❌ Ошибка: user_id должен быть числом")
    except Exception as e:
        logger.error("❌ Ошибка отправки подарка: %s", e)