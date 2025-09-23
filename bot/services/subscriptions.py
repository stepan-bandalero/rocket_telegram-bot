from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from bot.models.channels import Channel
from aiogram.exceptions import TelegramForbiddenError


async def check_subscriptions(session: AsyncSession, bot: Bot, user_id: int) -> list[Channel]:
    """
    Проверяет обязательные подписки пользователя.
    Возвращает список каналов, на которые не подписан.
    """
    stmt = select(Channel).where(Channel.is_required == True)
    result = await session.execute(stmt)
    channels = result.scalars().all()

    not_subscribed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.tg_id, user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(channel)
        except TelegramForbiddenError:
            # Бот не админ в канале → лучше логировать
            continue

    return not_subscribed
