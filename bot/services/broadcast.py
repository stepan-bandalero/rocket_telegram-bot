# bot/services/broadcast.py (улучшенная)
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.broadcast_task import BroadcastTask
from bot.db import SessionLocal


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
            status="draft"
        )
        BroadcastService.current_editing[user_id] = draft
        return draft

    # @staticmethod
    # async def send_task(bot: Bot, task: BroadcastTask, users: list[int]):
    #     task.status = "sending"
    #     task.total = len(users)
    #     task.sent = 0
    #     task.failed = 0
    #
    #     async with SessionLocal() as session:
    #         session.add(task)
    #         await session.commit()
    #
    #     stop_event = asyncio.Event()
    #     BroadcastService.stop_flags[task.id] = stop_event
    #
    #     for user_id in users:
    #         if stop_event.is_set():
    #             task.status = "stopped"
    #             break
    #
    #         try:
    #             await asyncio.sleep(0.1)
    #             # Основной контент
    #             if task.content_type == "text":
    #                 await BroadcastService._send_text(bot, user_id, task)
    #             elif task.content_type == "photo":
    #                 await BroadcastService._send_photo(bot, user_id, task)
    #             elif task.content_type == "video":
    #                 await BroadcastService._send_video(bot, user_id, task)
    #             elif task.content_type == "video_note":
    #                 await BroadcastService._send_video_note(bot, user_id, task)
    #
    #             task.sent += 1
    #         except Exception as e:
    #             task.failed += 1
    #
    #         # Обновляем прогресс каждые 100 отправок
    #         if task.sent % 100 == 0:
    #             try:
    #                 async with SessionLocal() as session:
    #                     session.add(task)
    #                     await session.commit()
    #             except Exception as e:
    #                 print(f"Ошибка сохранения прогресса: {e}")
    #
    #     if not stop_event.is_set():
    #         task.status = "done"
    #
    #     # Финализируем в БД
    #     async with SessionLocal() as session:
    #         session.add(task)
    #         await session.commit()
    #
    #     BroadcastService.stop_flags.pop(task.id, None)
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
                    await asyncio.sleep(0.1)
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
                if task.sent % 100 == 0:
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

    # bot/services/broadcast.py
    # @staticmethod
    # async def _send_text(bot: Bot, user_id: int, task: BroadcastTask):
    #     if task.buttons:
    #         kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in task.buttons]])
    #         await bot.send_message(user_id, task.text, reply_markup=kb, parse_mode="HTML")
    #     else:
    #         await bot.send_message(user_id, task.text, parse_mode="HTML")  # Всегда HTML
    #
    # @staticmethod
    # async def _send_photo(bot: Bot, user_id: int, task: BroadcastTask):
    #     if task.buttons:
    #         kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in task.buttons]])
    #         await bot.send_photo(user_id, task.media, caption=task.text, reply_markup=kb, parse_mode="HTML")
    #     else:
    #         await bot.send_photo(user_id, task.media, caption=task.text, parse_mode="HTML")  # Всегда HTML
    #
    # @staticmethod
    # async def _send_video(bot: Bot, user_id: int, task: BroadcastTask):
    #     if task.buttons:
    #         kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in task.buttons]])
    #         await bot.send_video(user_id, task.media, caption=task.text, reply_markup=kb, parse_mode="HTML")
    #     else:
    #         await bot.send_video(user_id, task.media, caption=task.text, parse_mode="HTML")  # Всегда HTML
    @staticmethod
    async def _send_text(bot: Bot, user_id: int, task: BroadcastTask):
        # Обработка кнопок
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if isinstance(buttons_data, list):
                    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in buttons_data]])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # Проверяем, это JSON с entities или обычный текст

        try:
            await bot.send_message(
                user_id,
                text=str(task.text) if task.text else None,
                reply_markup=kb,
                parse_mode="HTML"
            )
            return
        except:
            pass

        # Fallback: отправляем как текст
        await bot.send_message(
            user_id,
            text=str(task.text) if task.text else None,
            reply_markup=kb
        )

    @staticmethod
    async def _send_photo(bot: Bot, user_id: int, task: BroadcastTask):
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if isinstance(buttons_data, list):
                    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in buttons_data]])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        await bot.send_photo(
            user_id,
            str(task.media) if task.media else "",
            caption=str(task.text) if task.text else None,
            reply_markup=kb,
            parse_mode="HTML"  # ВКЛЮЧАЕМ HTML парсинг
        )

    @staticmethod
    async def _send_video(bot: Bot, user_id: int, task: BroadcastTask):
        kb = None
        if task.buttons:
            import json
            try:
                buttons_data = json.loads(str(task.buttons))
                if isinstance(buttons_data, list):
                    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in buttons_data]])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        await bot.send_video(
            user_id,
            str(task.media) if task.media else "",
            caption=str(task.text) if task.text else None,
            reply_markup=kb,
            parse_mode="HTML"  # ВКЛЮЧАЕМ HTML парсинг
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