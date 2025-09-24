from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.services.stats import send_admin_stats
from bot.utils.keyboards import broadcast_main_kb

router = Router()

#


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot, session):
    if message.from_user.id not in settings.admins:
        return
    await send_admin_stats(message, bot, session)


@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    """Быстрый доступ к рассылкам"""
    if message.from_user.id not in settings.admins:
        return

    await message.answer(
        "📊 **Управление рассылками**\n\n"
        "Выберите действие:",
        reply_markup=broadcast_main_kb()
    )