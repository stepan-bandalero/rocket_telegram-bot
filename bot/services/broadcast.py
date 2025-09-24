import asyncio
from aiogram import Bot
from bot.models.broadcast_task import BroadcastTask
from bot.db import async_session

class BroadcastService:
    stop_flags: dict[int, asyncio.Event] = {}

    @staticmethod
    async def send_task(bot: Bot, task: BroadcastTask, users: list[int]):
        task.status = "sending"
        task.sent = 0
        task.failed = 0
        BroadcastService.stop_flags[task.id] = asyncio.Event()

        for user_id in users:
            if BroadcastService.stop_flags[task.id].is_set():
                task.status = "stopped"
                break
            try:
                if task.content_type == "text":
                    await bot.send_message(user_id, task.text, parse_mode="HTML")
                elif task.content_type == "photo":
                    await bot.send_photo(user_id, task.media, caption=task.text or None, parse_mode="HTML")
                elif task.content_type == "video":
                    await bot.send_video(user_id, task.media, caption=task.text or None, parse_mode="HTML")
                elif task.content_type == "video_note":
                    await bot.send_video_note(user_id, task.media)
                    if task.text:
                        await bot.send_message(user_id, task.text, parse_mode="HTML")
                # Добавление inline-кнопок
                if task.buttons:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(**b) for b in task.buttons]]
                    )
                    await bot.send_message(user_id, task.text or " ", reply_markup=kb, parse_mode="HTML")

                task.sent += 1
            except Exception:
                task.failed += 1
        else:
            task.status = "done"

        # Очистка флага
        BroadcastService.stop_flags.pop(task.id, None)
        async with async_session() as session:
            session.add(task)
            await session.commit()
