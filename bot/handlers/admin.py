from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.services.stats import send_admin_stats

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot, session):
    if message.from_user.id not in settings.admins:
        return
    await send_admin_stats(message, bot, session)