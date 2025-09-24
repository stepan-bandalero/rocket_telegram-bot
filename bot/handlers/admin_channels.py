from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.manage_channels import ChannelService
from bot.config import settings

router = Router()


@router.message(F.text.startswith("/add_channel"))
async def add_channel(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    try:
        _, tg_id, title, url = message.text.split(maxsplit=3)
        tg_id = int(tg_id)
    except ValueError:
        await message.answer(
            "❌ Используй: <code>/add_channel tg_id title url</code>", parse_mode="HTML"
        )
        return

    channel = await ChannelService.add_channel(session, tg_id, title, url)
    await message.answer(f"✅ Канал <b>{channel.title}</b> добавлен.")


@router.message(F.text.startswith("/delete_channel"))
async def delete_channel(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    try:
        _, tg_id = message.text.split(maxsplit=1)
        tg_id = int(tg_id)
    except ValueError:
        await message.answer(
            "❌ Используй: <code>/delete_channel tg_id</code>", parse_mode="HTML"
        )
        return

    deleted = await ChannelService.delete_channel(session, tg_id)
    if deleted:
        await message.answer(f"🗑 Канал <code>{tg_id}</code> удален.")
    else:
        await message.answer("⚠ Канал не найден.")


@router.message(F.text.startswith("/channels"))
async def list_channels(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    channels = await ChannelService.get_channels(session)
    if not channels:
        await message.answer("📭 Список каналов пуст.")
        return

    lines = ["📋 <b>Список каналов</b>:\n"]
    for ch in channels:
        lines.append(
            f"▫️ <b>{ch.title}</b>\n"
            f"   🆔 <code>{ch.tg_id}</code>\n"
            f"   🔗 <a href=\"{ch.url}\">{ch.url}</a>\n"
        )

    text = "\n".join(lines)
    await message.answer(text, disable_web_page_preview=True)
