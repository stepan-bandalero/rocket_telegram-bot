# bot/handlers/broadcast.py (новый файл с улучшенной логикой)
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.db import SessionLocal
from bot.services.broadcast import BroadcastService
from bot.states.broadcast_states import BroadcastStates
from bot.utils.formatter import TelegramFormatter
from bot.utils.keyboards import (
    broadcast_main_kb,
    broadcast_constructor_kb,
    buttons_management_kb,
    button_type_kb,
    broadcast_active_kb,
    broadcast_control_kb
)

router = Router()


@router.callback_query(F.data == "broadcast_main")
async def broadcast_main(callback: CallbackQuery):
    """Главное меню рассылок"""
    await callback.message.edit_text(
        "📊 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=broadcast_main_kb()
    )


@router.callback_query(F.data == "broadcast_constructor")
async def broadcast_constructor(callback: CallbackQuery, state: FSMContext):
    """Конструктор рассылки"""
    user_id = callback.from_user.id

    # Создаем или получаем черновик
    if user_id not in BroadcastService.current_editing:
        draft = await BroadcastService.create_draft(user_id)
    else:
        draft = BroadcastService.current_editing[user_id]

    preview_text = await _generate_preview_text(draft)

    await callback.message.edit_text(
        f"🎨 <b>Конструктор рассылки</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_"))
async def edit_component(callback: CallbackQuery, state: FSMContext):
    """Редактирование компонентов рассылки"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    if callback.data == "edit_text":
        await state.set_state(BroadcastStates.editing_text)
        await callback.message.edit_text(
            "✏️ <b>Редактирование текста</b>\n\n"
            "Отправьте новый текст рассылки:",
            reply_markup=broadcast_constructor_kb(draft, is_editing=True)
        )

    elif callback.data == "edit_media":
        await state.set_state(BroadcastStates.editing_media)
        await callback.message.edit_text(
            "🖼️ <b>Редактирование медиа</b>\n\n"
            "Отправьте фото или видео:",
            reply_markup=broadcast_constructor_kb(draft, is_editing=True)
        )

    elif callback.data == "edit_buttons":
        await callback.message.edit_text(
            "🔘 <b>Управление кнопками</b>",
            reply_markup=buttons_management_kb()
        )

#
# @router.message(BroadcastStates.editing_text)
# async def process_text_edit(message: Message, state: FSMContext):
#     """Обработка нового текста"""
#     user_id = message.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         return
#
#     draft = BroadcastService.current_editing[user_id]
#     draft.text = message.text
#
#     preview_text = await _generate_preview_text(draft)
#     await message.answer(
#         f"✅ **Текст обновлен!**\n\n{preview_text}",
#         reply_markup=broadcast_constructor_kb(draft),
#         parse_mode="HTML"
#     )
#     await state.clear()
#
#
#
#
# @router.message(BroadcastStates.editing_media)
# async def process_media_edit(message: Message, state: FSMContext):
#     """Обработка нового медиа"""
#     user_id = message.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         return
#
#     draft = BroadcastService.current_editing[user_id]
#
#     if message.photo:
#         draft.content_type = "photo"
#         draft.media = message.photo[-1].file_id
#     elif message.video:
#         draft.content_type = "video"
#         draft.media = message.video.file_id
#     elif message.video_note:
#         draft.content_type = "video_note"
#         draft.media = message.video_note.file_id
#
#     preview_text = await _generate_preview_text(draft)
#     await message.answer(
#         f"✅ **Медиа обновлено!**\n\n{preview_text}",
#         reply_markup=broadcast_constructor_kb(draft),
#         parse_mode="HTML"
#     )
#     await state.clear()


# bot/handlers/broadcast.py
@router.message(BroadcastStates.editing_text)
async def process_text_edit(message: Message, state: FSMContext):
    """Обработка нового текста с преобразованием в HTML"""
    user_id = message.from_user.id
    if user_id not in BroadcastService.current_editing:
        return

    draft = BroadcastService.current_editing[user_id]

    # Преобразуем форматирование в HTML
    html_text = TelegramFormatter.entities_to_html(
        message.text or "",
        message.entities or []
    )

    draft.text = html_text  # Сохраняем как HTML

    preview_text = await _generate_preview_text(draft)
    await message.answer(
        f"✅ <b>Текст обновлен!</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )
    await state.clear()


@router.message(BroadcastStates.editing_media)
async def process_media_edit(message: Message, state: FSMContext):
    """Обработка нового медиа с преобразованием подписи в HTML"""
    user_id = message.from_user.id
    if user_id not in BroadcastService.current_editing:
        return

    draft = BroadcastService.current_editing[user_id]

    # Обрабатываем подпись если есть
    if message.caption:
        html_text = TelegramFormatter.entities_to_html(
            message.caption,
            message.caption_entities or []
        )
        draft.text = html_text  # Сохраняем как HTML
    elif not draft.text:  # Если текста еще нет
        draft.text = "📢 Ваш текст рассылки здесь..."

    # Обрабатываем медиа
    if message.photo:
        draft.content_type = "photo"
        draft.media = message.photo[-1].file_id
    elif message.video:
        draft.content_type = "video"
        draft.media = message.video.file_id
    elif message.video_note:
        draft.content_type = "video_note"
        draft.media = message.video_note.file_id

    preview_text = await _generate_preview_text(draft)
    await message.answer(
        f"✅ <b>Медиа обновлено!</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )
    await state.clear()



@router.callback_query(F.data.startswith("set_type_"))
async def set_content_type(callback: CallbackQuery):
    """Установка типа контента"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]
    content_type = callback.data.replace("set_type_", "")
    draft.content_type = content_type

    # Очищаем медиа при переходе на текст
    if content_type == "text":
        draft.media = None

    preview_text = await _generate_preview_text(draft)
    await callback.message.edit_text(
        f"✅ <b>Тип контента изменен!</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )


# @router.callback_query(F.data == "preview_broadcast")
# async def preview_broadcast(callback: CallbackQuery):
#     """Предпросмотр рассылки"""
#     user_id = callback.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         await callback.answer("Черновик не найден!")
#         return
#
#     draft = BroadcastService.current_editing[user_id]
#
#     try:
#         # Отправляем предпросмотр самому себе
#         if draft.content_type == "text":
#             await callback.message.answer(draft.text, parse_mode="HTML")
#         elif draft.content_type == "photo":
#             await callback.message.answer_photo(draft.media, caption=draft.text, parse_mode="HTML")
#         elif draft.content_type == "video":
#             await callback.message.answer_video(draft.media, caption=draft.text, parse_mode="HTML")
#         elif draft.content_type == "video_note":
#             await callback.message.answer_video_note(draft.media)
#             if draft.text:
#                 await callback.message.answer(draft.text, parse_mode="HTML")
#
#         await callback.answer("Предпросмотр отправлен!")
#     except Exception as e:
#         await callback.answer(f"Ошибка: {str(e)}")
#


# bot/handlers/broadcast.py
@router.callback_query(F.data == "preview_broadcast")
async def preview_broadcast(callback: CallbackQuery):
    """Предпросмотр с HTML форматированием"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    try:
        # Всегда используем parse_mode="HTML" для предпросмотра
        if draft.buttons:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**b) for b in draft.buttons]])
        else:
            kb = None

        if draft.content_type == "text":
            await callback.message.answer(draft.text, reply_markup=kb, parse_mode="HTML")
        elif draft.content_type == "photo":
            await callback.message.answer_photo(draft.media, caption=draft.text, reply_markup=kb, parse_mode="HTML")
        elif draft.content_type == "video":
            await callback.message.answer_video(draft.media, caption=draft.text, reply_markup=kb, parse_mode="HTML")
        elif draft.content_type == "video_note":
            await callback.message.answer_video_note(draft.media)
            if draft.text:
                await callback.message.answer(draft.text, reply_markup=kb, parse_mode="HTML")

        await callback.answer("Предпросмотр отправлен!")
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")


async def _generate_preview_text(draft) -> str:
    """Генерирует текст предпросмотра"""
    type_icons = {
        "text": "📝", "photo": "📷",
        "video": "🎥", "video_note": "📹"
    }

    text = (
        f"{type_icons.get(draft.content_type, '📝')} <b>Тип:</b> {draft.content_type}\n"
        f"📄 <b>Текст:</b> {draft.text[:100] + '...' if len(draft.text) > 100 else draft.text}\n"
    )

    if draft.media:
        text += f"🖼️ <b>Медиа:</b> ✅\n"

    text += f"🔘 <b>Кнопки:</b> {len(draft.buttons)} шт.\n"

    return text


# bot/handlers/broadcast.py (продолжение)

@router.callback_query(F.data == "add_button")
async def add_button_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления кнопки"""
    await callback.message.edit_text(
        "🔘 <b>Добавление кнопки</b>\n\n"
        "Выберите тип кнопки:",
        reply_markup=button_type_kb()
    )


@router.callback_query(F.data == "button_type_url")
async def add_url_button(callback: CallbackQuery, state: FSMContext):
    """Добавление URL-кнопки"""
    await state.set_state(BroadcastStates.editing_buttons)
    await state.update_data(button_type="url")

    await callback.message.edit_text(
        "🔗 <b>Добавление URL-кнопки</b>\n\n"
        "Отправьте текст кнопки и URL через запятую:\n"
        "Пример: <code>Мой сайт, https://example.com</code>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "button_type_webapp")
async def add_webapp_button(callback: CallbackQuery, state: FSMContext):
    """Добавление Web App кнопки"""
    await state.set_state(BroadcastStates.editing_buttons)
    await state.update_data(button_type="web_app")

    await callback.message.edit_text(
        "⚡ <b>Добавление Web App кнопки</b>\n\n"
        "Отправьте текст кнопки и URL Web App через запятую:\n"
        "Пример: <code>Открыть приложение, https://example.com</code>",
        parse_mode="HTML"
    )


@router.message(BroadcastStates.editing_buttons)
async def process_button_add(message: Message, state: FSMContext):
    """Обработка добавления кнопки"""
    user_id = message.from_user.id
    if user_id not in BroadcastService.current_editing:
        await message.answer("Черновик не найден!")
        return

    data = await state.get_data()
    button_type = data.get("button_type", "url")

    try:
        parts = message.text.split(',', 1)
        if len(parts) != 2:
            raise ValueError("Неверный формат")

        text = parts[0].strip()
        url = parts[1].strip()

        draft = BroadcastService.current_editing[user_id]

        if button_type == "url":
            new_button = {"text": text, "url": url}
        else:  # web_app
            new_button = {"text": text, "web_app": {"url": url}}

        draft.buttons.append(new_button)

        await message.answer(
            f"✅ <b>Кнопка добавлена!</b>\n\n"
            f"Текст: {text}\n"
            f"URL: {url}\n\n"
            f"Всего кнопок: {len(draft.buttons)}",
            reply_markup=buttons_management_kb()
        )

    except Exception as e:
        await message.answer(
            "❌ <b>Ошибка формата!</b>\n\n"
            "Пожалуйста, используйте формат:\n"
            "<code>Текст кнопки, https://example.com</code>",
            parse_mode="HTML"
        )

    await state.clear()


@router.callback_query(F.data == "edit_buttons_list")
async def edit_buttons_list(callback: CallbackQuery):
    """Редактирование списка кнопок"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    if not draft.buttons:
        await callback.answer("Нет кнопок для редактирования!")
        return

    buttons_text = "\n".join([
        f"{i + 1}. {btn['text']} - {btn.get('url', btn.get('web_app', {}).get('url', 'N/A'))}"
        for i, btn in enumerate(draft.buttons)
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        *[[InlineKeyboardButton(text=f"❌ Удалить {i + 1}", callback_data=f"remove_button_{i}")]
          for i in range(len(draft.buttons))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_buttons_management")]
    ])

    await callback.message.edit_text(
        f"🔘 <b>Редактирование кнопок</b>\n\n{buttons_text}",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("remove_button_"))
async def remove_button(callback: CallbackQuery):
    """Удаление кнопки"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    button_index = int(callback.data.replace("remove_button_", ""))
    draft = BroadcastService.current_editing[user_id]

    if 0 <= button_index < len(draft.buttons):
        removed_button = draft.buttons.pop(button_index)
        await callback.answer(f"Кнопка '{removed_button['text']}' удалена!")

        # Обновляем список кнопок
        await edit_buttons_list(callback)
    else:
        await callback.answer("Кнопка не найдена!")


@router.callback_query(F.data == "clear_buttons")
async def clear_buttons(callback: CallbackQuery):
    """Очистка всех кнопок"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]
    draft.buttons.clear()

    await callback.message.edit_text(
        "✅ <b>Все кнопки очищены!</b>",
        reply_markup=buttons_management_kb()
    )


@router.callback_query(F.data == "start_broadcast")
async def start_broadcast(callback: CallbackQuery):
    """Запуск рассылки"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    # Валидация
    if not draft.text and draft.content_type != "video_note":
        await callback.answer("Текст рассылки не может быть пустым!")
        return

    if draft.content_type in ["photo", "video"] and not draft.media:
        await callback.answer("Необходимо добавить медиа!")
        return

    # Запрашиваем подтверждение
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, запустить", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="back_constructor")]
    ])

    await callback.message.edit_text(
        "🚀 <b>Подтверждение запуска рассылки</b>\n\n"
        "Вы уверены, что хотите запустить рассылку?\n"
        f"Тип: {draft.content_type}\n"
        f"Кнопок: {len(draft.buttons)}",
        reply_markup=confirm_kb
    )


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, bot: Bot):
    """Подтверждение и запуск рассылки"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    # Получаем список пользователей для рассылки
    from bot.models.users import User
    async with SessionLocal() as session:
        result = await session.execute(select(User.telegram_id))
        users = [row[0] for row in result.all()]

    if not users:
        await callback.answer("Нет пользователей для рассылки!")
        return

    # Сохраняем задачу в БД
    draft.status = "pending"
    draft.total = len(users)

    async with SessionLocal() as session:
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

    # Запускаем рассылку в фоне
    asyncio.create_task(BroadcastService.send_task(bot, draft, users))

    # Убираем черновик из редактирования
    BroadcastService.current_editing.pop(user_id, None)

    await callback.message.edit_text(
        "✅ <b>Рассылка запущена!</b>\n\n"
        f"Получателей: {len(users)}\n"
        f"ID рассылки: #{draft.id}\n\n"
        "Отслеживать прогресс можно в разделе 'Активные рассылки'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Активные рассылки", callback_data="broadcast_active")],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="broadcast_main")]
        ])
    )


@router.callback_query(F.data == "broadcast_active")
async def broadcast_active_list(callback: CallbackQuery):
    """Список активных рассылок"""
    from bot.models.broadcast_task import BroadcastTask
    from sqlalchemy import select

    async with SessionLocal() as session:
        result = await session.execute(
            select(BroadcastTask).where(
                BroadcastTask.status.in_(["pending", "sending"])
            ).order_by(BroadcastTask.created_at.desc())
        )
        tasks = result.scalars().all()

    if not tasks:
        await callback.message.edit_text(
            "📊 <b>Активные рассылки</b>\n\n"
            "Нет активных рассылок.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
            ])
        )
        return

    await callback.message.edit_text(
        f"📊 <b>Активные рассылки</b>\n\nНайдено: {len(tasks)}",
        reply_markup=broadcast_active_kb(tasks)
    )


@router.callback_query(F.data.startswith("broadcast_info_"))
async def broadcast_info(callback: CallbackQuery):
    """Информация о конкретной рассылке"""
    task_id = int(callback.data.replace("broadcast_info_", ""))

    from bot.models.broadcast_task import BroadcastTask
    from sqlalchemy import select

    async with SessionLocal() as session:
        result = await session.execute(select(BroadcastTask).where(BroadcastTask.id == task_id))
        task = result.scalar_one_or_none()

    if not task:
        await callback.answer("Рассылка не найдена!")
        return

    status_icons = {
        "pending": "⏳", "sending": "🟢",
        "stopped": "🛑", "done": "✅", "draft": "📝"
    }

    progress = f"{task.sent}/{task.total}" if task.total > 0 else "0/0"
    percentage = (task.sent / task.total * 100) if task.total > 0 else 0

    info_text = (
        f"📋 <b>Информация о рассылке #{task.id}</b>\n\n"
        f"📊 <b>Статус:</b> {status_icons.get(task.status, '❓')} {task.status}\n"
        f"📈 <b>Прогресс:</b> {progress} ({percentage:.1f}%)\n"
        f"❌ <b>Ошибки:</b> {task.failed}\n"
        f"📝 <b>Тип:</b> {task.content_type}\n"
        f"🕒 <b>Создана:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔘 <b>Кнопок:</b> {len(task.buttons)}"
    )

    await callback.message.edit_text(
        info_text,
        reply_markup=broadcast_control_kb(task.id)
    )


@router.callback_query(F.data.startswith("stop_broadcast_"))
async def stop_broadcast(callback: CallbackQuery):
    """Остановка рассылки"""
    task_id = int(callback.data.replace("stop_broadcast_", ""))

    from bot.models.broadcast_task import BroadcastTask
    from sqlalchemy import select, update

    async with SessionLocal() as session:
        # Останавливаем рассылку
        await BroadcastService.stop_task(task_id)

        # Обновляем статус в БД
        await session.execute(
            update(BroadcastTask)
            .where(BroadcastTask.id == task_id)
            .values(status="stopped")
        )
        await session.commit()

    await callback.answer("✅ Рассылка остановлена!")
    await broadcast_info(callback)  # Обновляем информацию


@router.callback_query(F.data == "broadcast_history")
async def broadcast_history(callback: CallbackQuery):
    """История рассылок"""
    from bot.models.broadcast_task import BroadcastTask
    from sqlalchemy import select

    async with SessionLocal() as session:
        result = await session.execute(
            select(BroadcastTask)
            .where(BroadcastTask.status.in_(["done", "stopped"]))
            .order_by(BroadcastTask.created_at.desc())
            .limit(10)
        )
        tasks = result.scalars().all()

    if not tasks:
        await callback.message.edit_text(
            "📜 <b>История рассылок</b>\n\n"
            "Нет завершенных рассылок.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
            ])
        )
        return

    history_text = "📜 <b>История рассылок</b>\n\n"
    for task in tasks:
        status_icon = "✅" if task.status == "done" else "🛑"
        history_text += (
            f"{status_icon} #{task.id} - {task.sent}/{task.total} "
            f"({task.created_at.strftime('%d.%m.%Y')})\n"
        )

    await callback.message.edit_text(
        history_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
        ])
    )


@router.callback_query(F.data == "save_draft")
async def save_draft(callback: CallbackQuery):
    """Сохранение черновика"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]
    draft.status = "draft"

    async with SessionLocal() as session:
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

    await callback.answer(f"✅ Черновик сохранен! ID: #{draft.id}")


@router.callback_query(F.data == "save_editing")
async def save_editing(callback: CallbackQuery, state: FSMContext):
    """Сохранение редактирования"""
    await state.clear()
    user_id = callback.from_user.id

    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]
    preview_text = await _generate_preview_text(draft)

    await callback.message.edit_text(
        f"✅ <b>Изменения сохранены!</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_editing")
async def cancel_editing(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    await state.clear()
    user_id = callback.from_user.id

    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]
    preview_text = await _generate_preview_text(draft)

    await callback.message.edit_text(
        f"🎨 <b>Конструктор рассылки</b>\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        parse_mode="HTML"
    )


# Навигационные обработчики
@router.callback_query(F.data == "back_constructor")
async def back_to_constructor(callback: CallbackQuery):
    """Возврат в конструктор"""
    await broadcast_constructor(callback, None)


@router.callback_query(F.data == "back_buttons_management")
async def back_to_buttons_management(callback: CallbackQuery):
    """Возврат к управлению кнопками"""
    await callback.message.edit_text(
        "🔘 <b>Управление кнопками</b>",
        reply_markup=buttons_management_kb()
    )


@router.callback_query(F.data == "stop_all_broadcasts")
async def stop_all_broadcasts(callback: CallbackQuery):
    """Остановка всех рассылок"""
    from bot.models.broadcast_task import BroadcastTask
    from sqlalchemy import select, update

    async with SessionLocal() as session:
        # Останавливаем все активные рассылки
        result = await session.execute(
            select(BroadcastTask).where(BroadcastTask.status.in_(["pending", "sending"]))
        )
        tasks = result.scalars().all()

        for task in tasks:
            await BroadcastService.stop_task(task.id)
            await session.execute(
                update(BroadcastTask)
                .where(BroadcastTask.id == task.id)
                .values(status="stopped")
            )

        await session.commit()

    await callback.answer(f"✅ Остановлено {len(tasks)} рассылок!")
    await broadcast_active_list(callback)


@router.message(F.photo | F.video | F.video_note)
async def handle_media_message(message: Message, state: FSMContext):
    """Обработка медиа-сообщений для конструктора"""
    current_state = await state.get_state()
    if current_state != BroadcastStates.editing_media.state:
        return

    user_id = message.from_user.id
    if user_id not in BroadcastService.current_editing:
        return

    await process_media_edit(message, state)