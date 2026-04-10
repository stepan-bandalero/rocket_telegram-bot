

# bot/services/broadcast.py
import asyncio
import json
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, MessageEntity
from models.broadcast_task import BroadcastTask
from db import SessionLocal
from models.users import User
from sqlalchemy import select, update, func
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest


class BroadcastService:
    stop_flags: dict[int, asyncio.Event] = {}
    current_editing: dict[int, BroadcastTask] = {}  # Храним редактируемые задачи по user_id

    @staticmethod
    async def create_draft(user_id: int) -> BroadcastTask:
        """Создает черновик рассылки"""
        draft = BroadcastTask(
            content_type="text",
            text="📢 Ваш текст рассылки здесь...",
            buttons=[],
            status="draft",
            entities=None
        )
        BroadcastService.current_editing[user_id] = draft
        return draft

    # ------------------------- helpers -------------------------
    @staticmethod
    def build_keyboard_and_entities(task: BroadcastTask):
        kb = None
        entities = None

        if task.buttons:
            try:
                buttons_data = json.loads(str(task.buttons))
                keyboard_rows = [
                    [InlineKeyboardButton(**btn)] for btn in buttons_data
                ]
                if keyboard_rows:
                    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            except Exception as e:
                print(f"Ошибка парсинга кнопок: {e}")

        if task.entities:
            entities = [MessageEntity(**e) for e in task.entities]

        return kb, entities

    @staticmethod
    async def mark_blocked_bulk(user_ids: list[int]):
        if not user_ids:
            return
        async with SessionLocal() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id.in_(user_ids))
                .values(is_blocked=True)
            )
            await session.commit()

    @staticmethod
    async def save_progress(task: BroadcastTask):
        async with SessionLocal() as session:
            await session.execute(
                update(BroadcastTask)
                .where(BroadcastTask.id == task.id)
                .values(
                    sent=task.sent,
                    failed=task.failed,
                    status=task.status
                )
            )
            await session.commit()

    # ------------------------- основной метод -------------------------
    @staticmethod
    async def send_task(bot: Bot, task: BroadcastTask):

        stop_event = asyncio.Event()
        BroadcastService.stop_flags[task.id] = stop_event

        task.status = "sending"
        task.sent = 0
        task.failed = 0
        blocked_buffer = []

        async with SessionLocal() as session:
            # Считаем total и сохраняем
            count_result = await session.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_blocked.is_(False))
            )
            task.total = count_result.scalar() or 0
            session.add(task)
            await session.commit()

            # Подготавливаем keyboard и entities один раз
            kb, entities = BroadcastService.build_keyboard_and_entities(task)

            # Стримим пользователей
            result = await session.stream(
                select(User.telegram_id)
                .where(User.is_blocked.is_(False))
            )

            async for row in result:
                if stop_event.is_set():
                    task.status = "stopped"
                    break

                user_id = row[0]

                try:
                    if task.content_type == "text":
                        await bot.send_message(
                            user_id,
                            text=task.text,
                            entities=entities,
                            reply_markup=kb
                        )
                    elif task.content_type == "photo":
                        await bot.send_photo(
                            user_id,
                            task.media,
                            caption=task.text,
                            caption_entities=entities,
                            reply_markup=kb
                        )
                    elif task.content_type == "video":
                        await bot.send_video(
                            user_id,
                            task.media,
                            caption=task.text,
                            caption_entities=entities,
                            reply_markup=kb
                        )
                    elif task.content_type == "video_note":
                        await bot.send_video_note(user_id, task.media)
                        if task.text:
                            await bot.send_message(
                                user_id,
                                text=task.text,
                                entities=entities,
                                reply_markup=kb
                            )

                    task.sent += 1

                except TelegramForbiddenError:
                    task.failed += 1
                    blocked_buffer.append(user_id)

                except TelegramBadRequest:
                    task.failed += 1
                    # Можно фильтровать, но пока баним все BadRequest
                    blocked_buffer.append(user_id)

                except Exception:
                    task.failed += 1

                # Батчим блокировки и прогресс каждые 500 отправок
                if (task.sent + task.failed) % 500 == 0:
                    await BroadcastService.mark_blocked_bulk(blocked_buffer)
                    blocked_buffer.clear()
                    await BroadcastService.save_progress(task)

        # Сохраняем остаток буфера и финальный прогресс
        await BroadcastService.mark_blocked_bulk(blocked_buffer)
        blocked_buffer.clear()

        if task.status != "stopped":
            task.status = "done"
        await BroadcastService.save_progress(task)

        BroadcastService.stop_flags.pop(task.id, None)

    @staticmethod
    async def stop_task(task_id: int):
        if task_id in BroadcastService.stop_flags:
            BroadcastService.stop_flags[task_id].set()