# bot/services/broadcast.py (улучшенная)
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.broadcast_task import BroadcastTask
from bot.db import SessionLocal
from aiogram.types import MessageEntity


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

    @staticmethod
    async def send_task(bot: Bot, task: BroadcastTask, users: list[int]):
        try:
            task.status = "sending"
            task.total = len(users)
            task.sent = 0
            task.failed = 0

            async with SessionLocal() as session:
                session.add(task)
                await session.commit()

            stop_event = asyncio.Event()
            BroadcastService.stop_flags[task.id] = stop_event

            for i, user_id in enumerate(users):
                if stop_event.is_set():
                    task.status = "stopped"
                    break

                try:
                    # await asyncio.sleep(0.1)
                    # Основной контент
                    if task.content_type == "text":
                        await BroadcastService._send_text(bot, user_id, task)
                    elif task.content_type == "photo":
                        await BroadcastService._send_photo(bot, user_id, task)
                    elif task.content_type == "video":
                        await BroadcastService._send_video(bot, user_id, task)
                    elif task.content_type == "video_note":
                        await BroadcastService._send_video_note(bot, user_id, task)

                    task.sent += 1
                except:
                    task.failed += 1

                # Обновляем прогресс каждые 100 отправок
                if (task.sent + task.failed) % 100 == 0:
                    try:
                        async with SessionLocal() as session:
                            session.add(task)
                            await session.commit()
                    except Exception as e:
                        print(f"Ошибка сохранения прогресса: {e}")

            if not stop_event.is_set():
                task.status = "done"

            # Финализируем в БД
            async with SessionLocal() as session:
                session.add(task)
                await session.commit()

            BroadcastService.stop_flags.pop(task.id, None)

        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА в рассылке #{task.id}: {e}")
            # Меняем статус на ошибку
            task.status = "stopped"
            async with SessionLocal() as session:
                session.add(task)
                await session.commit()

    @staticmethod
    async def _send_text(bot: Bot, user_id: int, task: BroadcastTask):
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if buttons_data and isinstance(buttons_data, list):
                    keyboard_rows = []
                    for button_data in buttons_data:
                        try:
                            # Передаем все данные из словаря в конструктор InlineKeyboardButton
                            button = InlineKeyboardButton(**button_data)
                            keyboard_rows.append([button])
                        except Exception as e:
                            print(f"Ошибка создания кнопки: {e}")
                            continue
                    if keyboard_rows:
                        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                print(f"Ошибка парсинга кнопок: {e}")

        entities = None
        if task.entities:
            entities = [MessageEntity(**e) for e in task.entities]

        await bot.send_message(
            user_id,
            text=task.text if task.text else None,
            entities=entities,
            reply_markup=kb
        )


    @staticmethod
    async def _send_photo(bot: Bot, user_id: int, task: BroadcastTask):
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if buttons_data and isinstance(buttons_data, list):
                    keyboard_rows = []
                    for button_data in buttons_data:
                        try:
                            # Передаем все данные из словаря в конструктор InlineKeyboardButton
                            button = InlineKeyboardButton(**button_data)
                            keyboard_rows.append([button])
                        except Exception as e:
                            print(f"Ошибка создания кнопки: {e}")
                            continue
                    if keyboard_rows:
                        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                print(f"Ошибка парсинга кнопок: {e}")

        entities = None
        if task.entities:
            entities = [MessageEntity(**e) for e in task.entities]

        await bot.send_photo(
            user_id,
            task.media,
            caption=task.text if task.text else None,
            caption_entities=entities,
            reply_markup=kb
        )

    @staticmethod
    async def _send_video(bot: Bot, user_id: int, task: BroadcastTask):
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if buttons_data and isinstance(buttons_data, list):
                    keyboard_rows = []
                    for button_data in buttons_data:
                        try:
                            # Передаем все данные из словаря в конструктор InlineKeyboardButton
                            button = InlineKeyboardButton(**button_data)
                            keyboard_rows.append([button])
                        except Exception as e:
                            print(f"Ошибка создания кнопки: {e}")
                            continue
                    if keyboard_rows:
                        kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                print(f"Ошибка парсинга кнопок: {e}")


        entities = None
        if task.entities:
            entities = [MessageEntity(**e) for e in task.entities]

        await bot.send_video(
            user_id,
            task.media,
            caption=task.text if task.text else None,
            caption_entities=entities,
            reply_markup=kb
        )

    @staticmethod
    async def _send_video_note(bot: Bot, user_id: int, task: BroadcastTask):
        await bot.send_video_note(user_id, task.media)
        if task.text:
            await BroadcastService._send_text(bot, user_id, task)  # Будет использовать HTML

    @staticmethod
    async def stop_task(task_id: int):
        if task_id in BroadcastService.stop_flags:
            BroadcastService.stop_flags[task_id].set()