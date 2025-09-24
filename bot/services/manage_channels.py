from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.channels import Channel


class ChannelService:
    @staticmethod
    async def add_channel(session: AsyncSession, tg_id: int, title: str, url: str, is_required: bool = True) -> Channel:
        channel = Channel(
            tg_id=tg_id,
            title=title,
            url=url,
            is_required=is_required,
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
        return channel

    @staticmethod
    async def delete_channel(session: AsyncSession, tg_id: int) -> bool:
        result = await session.execute(select(Channel).where(Channel.tg_id == tg_id))
        channel = result.scalar_one_or_none()
        if channel:
            await session.delete(channel)
            await session.commit()
            return True
        return False

    @staticmethod
    async def get_channels(session: AsyncSession):
        result = await session.execute(select(Channel))
        return result.scalars().all()

    @staticmethod
    async def get_required_channels(session: AsyncSession):
        result = await session.execute(select(Channel).where(Channel.is_required == True))
        return result.scalars().all()
