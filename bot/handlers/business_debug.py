from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import BusinessConnection
from aiogram.methods import GetBusinessAccountGifts, GetAvailableGifts, GetBusinessConnection
import json
import logging

logger = logging.getLogger(__name__)

router = Router(name="business_debug")


# Ловим бизнес-сообщения
@router.business_message()
async def handle_business_message(message: types.Message):
    logger.info("💼 BusinessMessage raw: %s", message.json(indent=2, ensure_ascii=False))
    await message.answer("✅ BusinessMessage получен. Лог смотри в консоли.")


# Ловим апдейты business_connection (например, при подключении/отключении)
@router.business_connection()
async def handle_business_connection(bc: BusinessConnection):
    logger.info("🔗 BusinessConnection event:\n%s", bc.model_dump_json(indent=2, ensure_ascii=False))


# Команда: проверить текущее business_connection_id
@router.message(Command("my_business_conn"))
async def cmd_my_business_conn(message: types.Message):
    if message.business_connection_id:
        await message.answer(f"📎 business_connection_id: <code>{message.business_connection_id}</code>")
    else:
        await message.answer("❌ Нет business_connection_id в этом апдейте")


# Команда: получить полное описание business_connection (если id знаем)
@router.message(Command("debug_business_conn"))
async def cmd_debug_business_conn(message: types.Message, bot: Bot):
    if not message.business_connection_id:
        await message.answer("❌ В сообщении нет business_connection_id")
        return
    try:
        resp = await bot(GetBusinessConnection(business_connection_id=message.business_connection_id))
        logger.info("📑 GetBusinessConnection response:\n%s", resp.model_dump_json(indent=2, ensure_ascii=False))
        await message.answer("✅ GetBusinessConnection получен. Смотри лог.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при GetBusinessConnection: {e}")


# Команда: вытащить все подарки бизнес-аккаунта
@router.message(Command("debug_business_gifts"))
async def cmd_debug_business_gifts(message: types.Message, bot: Bot):
    if not message.business_connection_id:
        await message.answer("❌ Нет business_connection_id")
        return
    try:
        resp = await bot(GetBusinessAccountGifts(
            business_connection_id=message.business_connection_id,
            limit=100,
            offset=str(0)
        ))
        logger.info("🎁 GetBusinessAccountGifts response:\n%s", resp.model_dump_json(indent=2, ensure_ascii=False))
        await message.answer(f"✅ Найдено {len(resp.gifts)} подарков. Полный лог в консоли.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при GetBusinessAccountGifts: {e}")


# Команда: посмотреть список доступных подарков (что бот может отправить)
@router.message(Command("debug_available_gifts"))
async def cmd_debug_available_gifts(message: types.Message, bot: Bot):
    try:
        resp = await bot(GetAvailableGifts())
        logger.info("🎁 GetAvailableGifts response:\n%s", resp.model_dump_json(indent=2, ensure_ascii=False))
        await message.answer(f"✅ Доступно {len(resp.gifts)} подарков. Полный лог смотри в консоли.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при GetAvailableGifts: {e}")
