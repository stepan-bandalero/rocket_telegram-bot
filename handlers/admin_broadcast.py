# bot/handlers/broadcast.py (новый файл с улучшенной логикой)
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from aiogram.types import MessageEntity

from db import SessionLocal
from services.broadcast import BroadcastService
from states.broadcast_states import BroadcastStates
from utils.keyboards import (
    broadcast_main_kb,
    broadcast_constructor_kb,
    buttons_management_kb,
    button_type_kb,
    broadcast_active_kb,
    broadcast_control_kb,
)

from models.broadcast_task import BroadcastTask
from datetime import datetime, timedelta, timezone

from utils.broadcast_formatting import progress_bar, format_time_delta, decline_word

router = Router()

CASES_DATA = {
    # "case-1": {"name": "Free 24h", "cost_type": "free", "cost_value": 0},
    # "case-32": {"name": "Free", "cost_type": "free", "cost_value": 0},
    # "case-3": {"name": "Farm", "cost_type": "ton", "cost_value": 0.1},
    # "case-13": {"name": "Farm", "cost_type": "stars", "cost_value": 10},
    # "case-33": {"name": "Farm Cap", "cost_type": "stars", "cost_value": 15},
    # "case-22": {"name": "Heart", "cost_type": "ton", "cost_value": 1.2},
    # "case-26": {"name": "Heart", "cost_type": "stars", "cost_value": 120},
    # "case-23": {"name": "Arm", "cost_type": "ton", "cost_value": 1.8},
    # "case-27": {"name": "Arm", "cost_type": "stars", "cost_value": 180},
    # "case-5": {"name": "Oscar", "cost_type": "ton", "cost_value": 2.5},
    # "case-15": {"name": "Oscar", "cost_type": "stars", "cost_value": 250},
    # "case-6": {"name": "Perfume", "cost_type": "ton", "cost_value": 2.5},
    # "case-16": {"name": "Perfume", "cost_type": "stars", "cost_value": 250},
    # "case-30": {"name": "Winter", "cost_type": "ton", "cost_value": 4},
    # "case-31": {"name": "Winter", "cost_type": "stars", "cost_value": 400},
    # "case-7": {"name": "Magic", "cost_type": "ton", "cost_value": 5},
    # "case-18": {"name": "Magic", "cost_type": "stars", "cost_value": 500},
    # "case-24": {"name": "Snoop", "cost_type": "ton", "cost_value": 8},
    # "case-28": {"name": "Snoop", "cost_type": "stars", "cost_value": 800},
    # "case-9": {"name": "Ring", "cost_type": "ton", "cost_value": 10},
    # "case-19": {"name": "Ring", "cost_type": "stars", "cost_value": 1000},
    # "case-25": {"name": "Gem", "cost_type": "ton", "cost_value": 10},
    # "case-29": {"name": "Gem", "cost_type": "stars", "cost_value": 1000},
    # "case-8": {"name": "Cap", "cost_type": "ton", "cost_value": 25},
    # "case-20": {"name": "Cap", "cost_type": "stars", "cost_value": 2500},
    # "case-10": {"name": "VIP", "cost_type": "ton", "cost_value": 90},
    # "case-21": {"name": "VIP", "cost_type": "stars", "cost_value": 9000},
    # "case-35": {"name": "Peach", "cost_type": "ton", "cost_value": 1},
    # "case-36": {"name": "Peach", "cost_type": "stars", "cost_value": 100},
    # "case-39": {"name": "Durovs", "cost_type": "ton", "cost_value": 9.5},
    # "case-40": {"name": "Durovs", "cost_type": "stars", "cost_value": 950},
    # "case-41": {"name": "101 Roses", "cost_type": "ton", "cost_value": 0.99},
    # "case-42": {"name": "101 Roses", "cost_type": "stars", "cost_value": 99},
    # "case-43": {"name": "Her Day", "cost_type": "ton", "cost_value": 16.99},
    # "case-44": {"name": "Her Day", "cost_type": "stars", "cost_value": 1699},

    "case-50": {"name": "Free", "cost_type": "free", "cost_value": 0},
    "case-51": {"name": "Free Silver", "cost_type": "free", "cost_value": 0},
    "case-52": {"name": "Free Gold", "cost_type": "free", "cost_value": 0},
    "case-53": {"name": "Free Diamond", "cost_type": "free", "cost_value": 0},
    "case-55": {"name": "Winters", "cost_type": "stars", "cost_value": 49},
    "case-57": {"name": "Magic", "cost_type": "stars", "cost_value": 149},
    "case-59": {"name": "Love you", "cost_type": "stars", "cost_value": 299},
    "case-61": {"name": "Some case", "cost_type": "stars", "cost_value": 1699},
    "case-63": {"name": "Advanced", "cost_type": "stars", "cost_value": 799},
    "case-65": {"name": "Newcomer", "cost_type": "stars", "cost_value": 1299},
    "case-67": {"name": "Major", "cost_type": "stars", "cost_value": 2299},
    "case-69": {"name": "Business", "cost_type": "stars", "cost_value": 4999},
}

CASE_EMOJIS = {
    # "case-1": "5206502842478638898",  # Free 24h
    # "case-32": "5406756500108501710", # Free
    # "case-13": "5323420626893963255", # Farm (stars)
    # "case-33": "5323393091858631247", # Farm Cap
    # "case-26": "5294476812221439592", # Heart (stars)
    # "case-27": "5319126771994490119", # Arm (stars)
    # "case-15": "5283006569481525574", # Oscar (stars)
    # "case-16": "5272007523308689132", # Perfume (stars)
    # "case-31": "5449449325434266744", # Winter (stars)
    # "case-18": "5325685779760962109", # Magic (stars)
    # "case-28": "5438222109123834742", # Snoop (stars)
    # "case-19": "5352734865315881645", # Ring (stars)
    # "case-29": "5395476176527447827", # Gem (stars)
    # "case-20": "5330191715850541636", # Cap (stars)
    # "case-21": "5850233704739246397", # VIP (stars)
    # "case-36": "5292092955048302153", # Peach (stars)
    # "case-40": "5424698365210297589", # Durovs (stars)
    # "case-42": "5276453866727038041", # 101 Roses
    # "case-44": "5289670279960762852", # Her Day

    "case-50": "5395653021805860507", # free case
    "case-51": "5242392422427694330", # free silver
    "case-52": "5346117566253276549", # free gold
    "case-53": "5323710739049908981", # free diamond
    "case-55": "5406820323322521867", # winters
    "case-57": "5395779525772599106", # magic
    "case-59": "5289670279960762852",# love you
    "case-61": "5289749346013697883", # mystic case
    "case-63": "5395547339840577666", # advanced
    "case-65": "5294256463219291541", # newcomer
    "case-67": "5283006569481525574", # major
    "case-69": "5291963006517795791", # business

}



@router.message(BroadcastStates.waiting_forward, F.forward_origin | F.forward_from | F.forward_from_chat)
async def process_forwarded_message(message: Message, state: FSMContext):
    """Обработка пересланного сообщения (текст, фото, видео, видео-кружок)"""
    user_id = message.from_user.id


    draft = BroadcastService.current_editing[user_id]

    # Извлекаем текст/подпись и entities
    text = message.text or message.caption
    entities = message.entities or message.caption_entities

    if text:
        draft.text = text
        if entities:
            draft.entities = [
                {
                    "type": e.type,
                    "offset": e.offset,
                    "length": e.length,
                    "url": e.url,
                    "user": e.user.id if e.user else None,
                    "language": e.language,
                    "custom_emoji_id": e.custom_emoji_id,
                }
                for e in entities
            ]
        else:
            draft.entities = None
    elif not draft.text:
        draft.text = "📢 Текст отсутствует"

    # Извлекаем медиа
    if message.photo:
        draft.content_type = "photo"
        draft.media = message.photo[-1].file_id
    elif message.video:
        draft.content_type = "video"
        draft.media = message.video.file_id
    elif message.video_note:
        draft.content_type = "video_note"
        draft.media = message.video_note.file_id
    # Если это просто текст — оставляем текущий тип (или ставим text)
    elif message.text:
        draft.content_type = "text"
        draft.media = None
    # Если ничего не подошло (например, стикер) — сообщим об ошибке
    else:
        await message.answer("❌ Неподдерживаемый тип сообщения. Отправьте текст, фото, видео или видео-кружок.")
        return

    # Сообщаем об успехе и показываем предпросмотр
    preview_text = await _generate_preview_text(draft)
    await message.answer(
        f"✅ Данные из пересланного сообщения сохранены!\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft)
    )
    await state.clear()



@router.callback_query(F.data == "broadcast_main")
async def broadcast_main(callback: CallbackQuery):
    """Главное меню рассылок"""
    await callback.message.edit_text(
        "📊 Управление рассылками\n\n"
        "Выберите действие:",
        reply_markup=broadcast_main_kb()
    )


@router.callback_query(F.data == "broadcast_constructor")
async def broadcast_constructor(callback: CallbackQuery):
    """Конструктор рассылки"""
    user_id = callback.from_user.id

    # Создаем или получаем черновик
    if user_id not in BroadcastService.current_editing:
        draft = await BroadcastService.create_draft(user_id)
    else:
        draft = BroadcastService.current_editing[user_id]

    preview_text = await _generate_preview_text(draft)

    await callback.message.edit_text(
        f"🎨 Конструктор рассылки\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        # parse_mode="HTML"
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
            "✏️ Редактирование текста\n\n"
            "Отправьте новый текст рассылки:",
            reply_markup=broadcast_constructor_kb(draft, is_editing=True)
        )

    elif callback.data == "edit_media":
        await state.set_state(BroadcastStates.editing_media)
        await callback.message.edit_text(
            "🖼️ Редактирование медиа\n\n"
            "Отправьте фото или видео:",
            reply_markup=broadcast_constructor_kb(draft, is_editing=True)
        )

    elif callback.data == "edit_buttons":
        await callback.message.edit_text(
            "🔘 Управление кнопками",
            reply_markup=buttons_management_kb()
        )



@router.message(BroadcastStates.editing_text)
async def process_text_edit(message: Message, state: FSMContext):
    """Обработка нового текста"""
    user_id = message.from_user.id
    if user_id not in BroadcastService.current_editing:
        return

    draft = BroadcastService.current_editing[user_id]

    draft.text = message.text or ""

    if message.entities:
        draft.entities = [
            {
                "type": e.type,
                "offset": e.offset,
                "length": e.length,
                "url": e.url,
                "user": e.user.id if e.user else None,
                "language": e.language,
                "custom_emoji_id": e.custom_emoji_id,
            }
            for e in message.entities
        ]
    else:
        draft.entities = None



    entities = None
    if draft.entities:
        entities = [MessageEntity(**e) for e in draft.entities]

    await message.answer(
        draft.text,
        entities=entities,
        reply_markup=broadcast_constructor_kb(draft)
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

        draft.text = message.caption

        if message.caption_entities:
            draft.entities = [
                {
                    "type": e.type,
                    "offset": e.offset,
                    "length": e.length,
                    "url": e.url,
                    "user": e.user.id if e.user else None,
                    "language": e.language,
                    "custom_emoji_id": e.custom_emoji_id,
                }
                for e in message.caption_entities
            ]
        else:
            draft.entities = None

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
        f"✅ Медиа обновлено!\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        # parse_mode="HTML"
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
        f"✅ Тип контента изменен!\n\n{preview_text}",
        reply_markup=broadcast_constructor_kb(draft),
        # parse_mode="HTML"
    )


@router.callback_query(F.data == "preview_broadcast")
async def preview_broadcast(callback: CallbackQuery):
    """Предпросмотр с HTML форматированием"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    entities = None
    if draft.entities:
        entities = [MessageEntity(**e) for e in draft.entities]


    try:
        # Обработка кнопок
        # kb = None
        # if draft.buttons:
        #     import json
        #     try:
        #         buttons_data = json.loads(str(draft.buttons))
        #         if buttons_data and isinstance(buttons_data, list):
        #             # Создаем кнопки с проверкой структуры
        #             keyboard_rows = []
        #             for button_data in buttons_data:
        #                 try:
        #                     if 'text' in button_data:
        #                         if 'url' in button_data:
        #                             button = InlineKeyboardButton(
        #                                 text=button_data['text'],
        #                                 url=button_data['url']
        #                             )
        #                         elif 'web_app' in button_data:
        #                             button = InlineKeyboardButton(
        #                                 text=button_data['text'],
        #                                 web_app=button_data['web_app']
        #                             )
        #                         else:
        #                             continue
        #                         keyboard_rows.append([button])
        #                 except (KeyError, TypeError):
        #                     continue
        #
        #             if keyboard_rows:
        #                 kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        #     except (json.JSONDecodeError, TypeError, ValueError) as e:
        #         print(f"Ошибка парсинга кнопок: {e}")
        # Обработка кнопок
        kb = None
        if draft.buttons:
            import json
            try:
                buttons_data = json.loads(str(draft.buttons))
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

        # Получаем значения
        content_type = draft.content_type or "text"
        text = draft.text or ""
        media = draft.media

        if not text and content_type != "video_note":
            await callback.answer("Текст для предпросмотра отсутствует!")
            return

        # Отправляем предпросмотр в зависимости от типа контента
        if content_type == "text":

            await callback.message.answer(
                text,
                entities=entities,
                reply_markup=kb
            )


        elif content_type == "photo":
            if not media:
                await callback.answer("Фото для предпросмотра отсутствует!")
                return

            await callback.message.answer_photo(
                media,
                caption=text if text else None,
                caption_entities=entities,
                reply_markup=kb
            )


        elif content_type == "video":
            if not media:
                await callback.answer("Видео для предпросмотра отсутствует!")
                return
            await callback.message.answer_video(
                media,
                caption=text if text else None,
                reply_markup=kb,
                caption_entities=entities

                # parse_mode="HTML"
            )

        elif content_type == "video_note":
            if not media:
                await callback.answer("Кружочное видео для предпросмотра отсутствует!")
                return
            await callback.message.answer_video_note(media)
            if text:

                await callback.message.answer(
                    text,
                    entities=entities,
                    reply_markup=kb
                )

        await callback.answer("✅ Предпросмотр отправлен!")

    except Exception as e:
        print(f"Ошибка при предпросмотре: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def _generate_preview_text(draft) -> str:
    """Генерирует текст предпросмотра"""
    type_icons = {
        "text": "📝",
        "photo": "📷",
        "video": "🎥",
        "video_note": "📹"
    }

    # Безопасное получение значений
    content_type = draft.content_type or "text"
    text = draft.text or "Нет текста"

    # Обрезаем текст для предпросмотра (убираем HTML теги для отображения)
    import re
    # clean_text = re.sub('<.*?>', '', text)  # Удаляем HTML теги
    # text_preview = clean_text[:100] + '...' if len(clean_text) > 100 else clean_text
    text_preview = text[:100] + '...' if len(text) > 100 else text

    # Собираем текст предпросмотра
    preview_parts = [
        f"{type_icons.get(content_type, '📝')} Тип: {content_type}",
        f"📄 Текст: {text_preview}"
    ]

    if draft.media:
        preview_parts.append("🖼️ Медиа: ✅")


    return "\n".join(preview_parts)
#
# @router.callback_query(F.data == "add_button")
# async def add_button_start(callback: CallbackQuery):
#     """Начало добавления кнопки"""
#     await callback.message.edit_text(
#         "🔘 Добавление кнопки\n\n"
#         "Выберите тип кнопки:",
#         reply_markup=button_type_kb()
#     )
#
#
# @router.callback_query(F.data == "button_type_url")
# async def add_url_button(callback: CallbackQuery, state: FSMContext):
#     """Добавление URL-кнопки"""
#     await state.set_state(BroadcastStates.editing_buttons)
#     await state.update_data(button_type="url")
#
#     await callback.message.edit_text(
#         "🔗 <b>Добавление URL-кнопки</b>\n\n"
#         "Отправьте текст кнопки и URL через запятую:\n"
#         "Пример: <code>Мой сайт, https://example.com</code>",
#         parse_mode="HTML"
#     )
#
#
# @router.callback_query(F.data == "button_type_webapp")
# async def add_webapp_button(callback: CallbackQuery, state: FSMContext):
#     """Добавление Web App кнопки"""
#     await state.set_state(BroadcastStates.editing_buttons)
#     await state.update_data(button_type="web_app")
#
#     await callback.message.edit_text(
#         "⚡ <b>Добавление Web App кнопки</b>\n\n"
#         "Отправьте текст кнопки и URL Web App через запятую:\n"
#         "Пример: <code>Открыть приложение, https://example.com</code>",
#         parse_mode="HTML"
#     )
#
#
# @router.message(BroadcastStates.editing_buttons)
# async def process_button_add(message: Message, state: FSMContext):
#     """Обработка добавления кнопки"""
#     user_id = message.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         await message.answer("Черновик не найден!")
#         return
#
#     data = await state.get_data()
#     button_type = data.get("button_type", "url")
#
#     try:
#         parts = message.text.split(',', 1)
#         if len(parts) != 2:
#             raise ValueError("Неверный формат")
#
#         text = parts[0].strip()
#         url = parts[1].strip()
#
#         draft = BroadcastService.current_editing[user_id]
#
#         if button_type == "url":
#             new_button = {"text": text, "url": url}
#         else:  # web_app
#             new_button = {"text": text, "web_app": {"url": url}}
#
#         # Сохраняем кнопки как JSON строку
#         import json
#         current_buttons = []
#         if draft.buttons:
#             try:
#                 current_buttons = json.loads(str(draft.buttons))  # Явное преобразование
#                 if not isinstance(current_buttons, list):
#                     current_buttons = []
#             except (json.JSONDecodeError, TypeError, ValueError):
#                 current_buttons = []
#
#         current_buttons.append(new_button)
#         draft.buttons = json.dumps(current_buttons)  # Сохраняем как JSON строку
#
#         await message.answer(
#             f"✅ <b>Кнопка добавлена!</b>\n\n"
#             f"Текст: {text}\n"
#             f"URL: {url}\n\n"
#             f"Всего кнопок: {len(current_buttons)}",
#             reply_markup=buttons_management_kb()
#         )
#
#     except Exception as e:
#         await message.answer(
#             "❌ <b>Ошибка формата!</b>\n\n"
#             "Пожалуйста, используйте формат:\n"
#             "<code>Текст кнопки, https://example.com</code>",
#             parse_mode="HTML"
#         )
#
#     await state.clear()
#
#
# @router.callback_query(F.data == "edit_buttons_list")
# async def edit_buttons_list(callback: CallbackQuery):
#     """Редактирование списка кнопок"""
#     user_id = callback.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         await callback.answer("Черновик не найден!")
#         return
#
#     draft = BroadcastService.current_editing[user_id]
#
#     # Распарсим кнопки из JSON
#     buttons_list = []
#     if draft.buttons:
#         import json
#         try:
#             buttons_list = json.loads(str(draft.buttons))  # Явное преобразование в str
#             if not isinstance(buttons_list, list):
#                 buttons_list = []
#         except (json.JSONDecodeError, TypeError, ValueError):
#             buttons_list = []
#
#     if not buttons_list:
#         await callback.answer("Нет кнопок для редактирования!")
#         return
#
#     # Генерация текста с кнопками
#     buttons_text = "\n".join([
#         f"{i + 1}. {btn['text']} - {btn.get('url', btn.get('web_app', {}).get('url', 'N/A'))}"
#         for i, btn in enumerate(buttons_list)
#     ])
#
#     # Генерация клавиатуры для удаления
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         *[[InlineKeyboardButton(text=f"❌ Удалить {i + 1}", callback_data=f"remove_button_{i}")]
#           for i in range(len(buttons_list))],
#         [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_buttons_management")]
#     ])
#
#     await callback.message.edit_text(
#         f"🔘 Редактирование кнопок\n\n{buttons_text}",
#         reply_markup=keyboard
#     )
#
#
# @router.callback_query(F.data.startswith("remove_button_"))
# async def remove_button(callback: CallbackQuery):
#     """Удаление кнопки"""
#     user_id = callback.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         await callback.answer("Черновик не найден!")
#         return
#
#     button_index = int(callback.data.replace("remove_button_", ""))
#     draft = BroadcastService.current_editing[user_id]
#
#     # Распарсим текущие кнопки
#     import json
#     current_buttons = []
#     if draft.buttons:
#         try:
#             current_buttons = json.loads(str(draft.buttons))
#             if not isinstance(current_buttons, list):
#                 current_buttons = []
#         except (json.JSONDecodeError, TypeError, ValueError):
#             current_buttons = []
#
#     # Удаляем кнопку по индексу
#     if 0 <= button_index < len(current_buttons):
#         removed_button = current_buttons.pop(button_index)
#
#         # Сохраняем обновленный список
#         draft.buttons = json.dumps(current_buttons)
#
#         await callback.answer(f"Кнопка '{removed_button['text']}' удалена!")
#
#         # Обновляем список кнопок
#         await edit_buttons_list(callback)
#     else:
#         await callback.answer("Кнопка не найдена!")
#
#
@router.callback_query(F.data == "clear_buttons")
async def clear_buttons(callback: CallbackQuery):
    """Очистка всех кнопок"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    # Просто устанавливаем пустой JSON массив
    import json
    draft.buttons = json.dumps([])

    await callback.message.edit_text(
        "✅ Все кнопки очищены!",
        reply_markup=buttons_management_kb()
    )

@router.callback_query(F.data == "add_button")
async def add_button_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления кнопки (сразу запрашиваем текст)"""
    await state.clear()
    await state.set_state(BroadcastStates.adding_button_text)
    await callback.message.edit_text(
        "🔘 Добавление кнопки\n\n"
        "Введите текст кнопки:"
    )


@router.message(BroadcastStates.adding_button_text)
async def process_button_text(message: Message, state: FSMContext):
    """Обработка текста кнопки"""
    text = message.text.strip()
    if not text:
        await message.answer("Текст не может быть пустым. Введите текст кнопки:")
        return
    await state.update_data(button_text=text)

    # Предлагаем выбор способа создания ссылки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ввести URL вручную", callback_data="webapp_manual_url")],
        [InlineKeyboardButton(text="🎯 Создать для RocketxAppBot", callback_data="webapp_bot_params")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_button")]
    ])
    await message.answer(
        "Выберите способ указания ссылки для Web App:",
        reply_markup=kb
    )
    # Оставляем состояние — дальше обработаем callback


@router.callback_query(F.data == "webapp_manual_url")
async def webapp_manual_url(callback: CallbackQuery, state: FSMContext):
    """Ручной ввод URL"""
    await state.set_state(BroadcastStates.adding_button_url)
    await callback.message.edit_text("Введите URL (начинается с http:// или https://):")


@router.callback_query(F.data == "webapp_bot_params")
async def webapp_bot_params(callback: CallbackQuery, state: FSMContext):
    """Создание ссылки через параметры RocketxAppBot"""
    await state.set_state(BroadcastStates.adding_button_page)

    # Клавиатура со страницами
    pages = [
        ("cases", "📦 Cases"),
        ("fortune", "🎡 Fortune"),
        ("staking", "📈 Staking"),
        ("plinko", "🎰 Plinko"),
        ("spin", "🎡 Spin"),
        ("profile", "👤 Profile"),
        ("games", "🎮 Games"),
        ("lottery", "🎲 Lottery"),
        ("upgrade", "⬆️ Upgrade"),
        ("friends", "👥 Friends"),
        ("none", "🚫 Без страницы (просто запуск)"),
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"page_{page}")] for page, name in pages
    ])
    await callback.message.edit_text(
        "Выберите страницу для открытия в приложении:",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("page_"), BroadcastStates.adding_button_page)
async def process_page_selection(callback: CallbackQuery, state: FSMContext):
    """Выбрана страница для Web App"""
    page = callback.data.replace("page_", "")
    if page == "none":
        page = None
    await state.update_data(webapp_page=page)

    # if page == "cases":
    #     await state.set_state(BroadcastStates.adding_button_case)
    #
    #     # Формируем клавиатуру с кейсами (только free и stars)
    #     buttons = []
    #     for case_id, info in CASES_DATA.items():
    #         if info['cost_type'] in ('free', 'stars'):
    #             if info['cost_type'] == 'free':
    #                 cost_display = "Бесплатно"
    #             else:
    #                 cost_display = f"{info['cost_value']} ⭐"
    #             buttons.append(
    #                 InlineKeyboardButton(
    #                     text=f"{info['name']} - {cost_display}",
    #                     callback_data=f"case_{case_id}"
    #                 )
    #             )
    #     # Разбивка по 2
    #     rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    #     rows.append([InlineKeyboardButton(text="🚫 Без кейса", callback_data="case_none")])
    #     kb = InlineKeyboardMarkup(inline_keyboard=rows)
    #     await callback.message.edit_text(
    #         "Выберите кейс:",
    #         reply_markup=kb
    #     )
    if page == "cases":
        await state.set_state(BroadcastStates.adding_button_case)

        buttons = []
        for case_id, info in CASES_DATA.items():
            if info['cost_type'] in ('free', 'stars'):
                if info['cost_type'] == 'free':
                    cost_display = "Бесплатно"
                else:
                    cost_display = f"{info['cost_value']} ⭐"

                # Получаем ID эмодзи для данного кейса (если есть)
                emoji_id = CASE_EMOJIS.get(case_id)

                # Создаём кнопку с учётом наличия эмодзи
                button_kwargs = {
                    "text": f"{info['name']} - {cost_display}",
                    "callback_data": f"case_{case_id}"
                }
                if emoji_id:
                    button_kwargs["icon_custom_emoji_id"] = emoji_id

                button = InlineKeyboardButton(**button_kwargs)
                buttons.append(button)

        # Разбивка по 2
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        rows.append([InlineKeyboardButton(text="🚫 Без кейса", callback_data="case_none")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        await callback.message.edit_text("Выберите кейс:", reply_markup=kb)
    else:
        # Для других страниц сразу формируем URL
        await build_webapp_url_and_next(state, callback)


@router.callback_query(F.data.startswith("case_"), BroadcastStates.adding_button_case)
async def process_case_selection(callback: CallbackQuery, state: FSMContext):
    """Выбран конкретный кейс"""
    case = callback.data.replace("case_", "")
    if case == "none":
        case = None
    await state.update_data(webapp_case=case)
    await build_webapp_url_and_next(state, callback)


async def build_webapp_url_and_next(state: FSMContext, callback: CallbackQuery):
    """Формирует URL для RocketxAppBot и переходит к выбору стиля"""
    data = await state.get_data()
    page = data.get('webapp_page')
    case = data.get('webapp_case')
    base_url = "https://t.me/RocketxAppBot/rocketapp?startapp="
    if page:
        url = base_url + f"page__{page}"
        if page == "cases" and case:
            url += f"--{case}"
    else:
        url = base_url  # без параметров
    await state.update_data(button_url=url)
    await go_to_style_selection(callback, state)


@router.message(BroadcastStates.adding_button_url)
async def process_button_url(message: Message, state: FSMContext):
    """Обработка введённого URL"""
    url = message.text.strip()
    if not url.startswith(('http://', 'https://')):
        await message.answer("URL должен начинаться с http:// или https://. Попробуйте снова:")
        return
    await state.update_data(button_url=url)
    await go_to_style_selection(message, state)


async def go_to_style_selection(target, state: FSMContext):
    """Переход к выбору стиля (общая функция)"""
    await state.set_state(BroadcastStates.adding_button_style)
    style_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Primary", callback_data="style_primary")],
        [InlineKeyboardButton(text="🟢 Success", callback_data="style_success")],
        [InlineKeyboardButton(text="🔴 Danger", callback_data="style_danger")],
        [InlineKeyboardButton(text="⚪ Без стиля", callback_data="style_none")]
    ])
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(
            "Выберите стиль кнопки (или пропустите):",
            reply_markup=style_kb
        )
    else:
        await target.answer(
            "Выберите стиль кнопки (или пропустите):",
            reply_markup=style_kb
        )


@router.callback_query(F.data.startswith("style_"), BroadcastStates.adding_button_style)
async def process_style_selection(callback: CallbackQuery, state: FSMContext):
    """Выбран стиль кнопки"""
    style = callback.data.replace("style_", "")
    if style == "none":
        style = None
    await state.update_data(button_style=style)
    await state.set_state(BroadcastStates.adding_button_emoji)
    await callback.message.edit_text(
        "Отправьте одно кастомное эмодзи (или отправьте /skip чтобы пропустить):"
    )


@router.message(BroadcastStates.adding_button_emoji)
async def process_button_emoji(message: Message, state: FSMContext):
    """Обработка ввода кастомного эмодзи (извлекаем ID)"""
    # Проверка на /skip
    if message.text and message.text.strip() == "/skip":
        await state.update_data(button_emoji=None)
        await show_button_confirmation(message, state)
        return

    # Ищем custom_emoji в entities
    if message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji" and entity.custom_emoji_id:
                emoji_id = entity.custom_emoji_id
                await state.update_data(button_emoji=emoji_id)
                await show_button_confirmation(message, state)
                return

    # Если не нашли
    await message.answer(
        "❌ Не удалось найти кастомный эмодзи в сообщении.\n"
        "Пожалуйста, отправьте одно сообщение с кастомным эмодзи (или /skip чтобы пропустить)."
    )
    # Остаёмся в том же состоянии


@router.message(BroadcastStates.adding_button_emoji, F.text == "/skip")
async def skip_emoji(message: Message, state: FSMContext):
    """Пропуск ввода эмодзи"""
    await state.update_data(button_emoji=None)
    await show_button_confirmation(message, state)


async def show_button_confirmation(message: Message, state: FSMContext):
    """Показать предпросмотр и запросить подтверждение"""
    data = await state.get_data()
    # Обязательные поля
    text = data.get('button_text')
    url = data.get('button_url')

    if not text or not url:
        await message.answer("Ошибка: не хватает данных для создания кнопки. Начните заново.")
        await state.clear()
        return

    style = data.get('button_style')
    emoji = data.get('button_emoji')

    preview = f"Текст: {text}\nURL: {url}"
    if style:
        preview += f"\nСтиль: {style}"
    if emoji:
        preview += f"\nEmoji ID: {emoji}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="confirm_add_button", style="success")],
        [InlineKeyboardButton(text="🔄 Заново", callback_data="restart_add_button", style="primary")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add_button", style="danger")]
    ])
    await message.answer(
        f"Проверьте параметры кнопки:\n\n{preview}\n\nВсё верно?",
        reply_markup=kb
    )
    await state.set_state(BroadcastStates.adding_button_confirm)


@router.callback_query(F.data == "confirm_add_button", BroadcastStates.adding_button_confirm)
async def confirm_add_button(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и сохранение кнопки"""
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        await state.clear()
        return

    draft = BroadcastService.current_editing[user_id]
    data = await state.get_data()

    # Формируем объект кнопки (всегда web_app)
    button = {
        "text": data['button_text'],
        "url": data['button_url']  # просто строка
    }
    if data.get('button_style'):
        button['style'] = data['button_style']
    if data.get('button_emoji'):
        button['icon_custom_emoji_id'] = data['button_emoji']

    # Сохраняем в черновик
    import json
    current_buttons = []
    if draft.buttons:
        try:
            current_buttons = json.loads(str(draft.buttons))
            if not isinstance(current_buttons, list):
                current_buttons = []
        except Exception:
            current_buttons = []

    current_buttons.append(button)
    draft.buttons = json.dumps(current_buttons)

    await callback.message.edit_text(
        f"✅ Кнопка добавлена!\n\nВсего кнопок: {len(current_buttons)}",
        reply_markup=buttons_management_kb()
    )
    await state.clear()


@router.callback_query(F.data == "restart_add_button")
async def restart_add_button(callback: CallbackQuery, state: FSMContext):
    """Начать добавление заново"""
    await add_button_start(callback, state)


@router.callback_query(F.data == "cancel_add_button")
async def cancel_add_button(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления кнопки"""
    await state.clear()
    await callback.message.edit_text(
        "Добавление кнопки отменено.",
        reply_markup=buttons_management_kb()
    )


@router.callback_query(F.data == "restart_add_button")
async def restart_add_button(callback: CallbackQuery, state: FSMContext):
    """Начать добавление заново"""
    await state.clear()
    await add_button_start(callback, state)


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
            [
                InlineKeyboardButton(
                    text="✅ Да, запустить",
                    callback_data="confirm_broadcast",
                    style="success"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="back_constructor",
                    style="danger"
                )
            ],
        ])


    await callback.message.edit_text(
        "🚀 Подтверждение запуска рассылки\n\n"
        "Вы уверены, что хотите запустить рассылку?",
        reply_markup=confirm_kb
    )

#
# @router.callback_query(F.data == "confirm_broadcast")
# async def confirm_broadcast(callback: CallbackQuery, bot: Bot):
#     """Подтверждение и запуск рассылки"""
#     user_id = callback.from_user.id
#     if user_id not in BroadcastService.current_editing:
#         await callback.answer("Черновик не найден!")
#         return
#
#     draft = BroadcastService.current_editing[user_id]
#
#     # Получаем список пользователей для рассылки
#     from bot.models.users import User
#     async with SessionLocal() as session:
#         result = await session.execute(select(User.telegram_id))
#         users = [row[0] for row in result.all()]
#
#     if not users:
#         await callback.answer("Нет пользователей для рассылки!")
#         return
#
#     # Сохраняем задачу в БД
#     draft.status = "pending"
#     draft.total = len(users)
#
#     async with SessionLocal() as session:
#         session.add(draft)
#         await session.commit()
#         await session.refresh(draft)
#
#     # Запускаем рассылку в фоне
#     asyncio.create_task(BroadcastService.send_task(bot, draft, users))
#
#     # Убираем черновик из редактирования
#     BroadcastService.current_editing.pop(user_id, None)
#
#     await callback.message.edit_text(
#         "✅ Рассылка запущена!\n\n"
#         f"Получателей: {len(users)}\n"
#         f"ID рассылки: #{draft.id}\n\n"
#         "Отслеживать прогресс можно в разделе 'Активные рассылки'",
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="📊 Активные рассылки", callback_data="broadcast_active")],
#             [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="broadcast_main")]
#         ])
#     )


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, bot: Bot):

    user_id = callback.from_user.id

    if user_id not in BroadcastService.current_editing:
        await callback.answer("Черновик не найден!")
        return

    draft = BroadcastService.current_editing[user_id]

    draft.status = "pending"

    async with SessionLocal() as session:
        session.add(draft)
        await session.commit()
        await session.refresh(draft)

    asyncio.create_task(
        BroadcastService.send_task(bot, draft)
    )

    BroadcastService.current_editing.pop(user_id, None)

    await callback.message.edit_text(
        f"✅ Рассылка запущена!\n\n"
        f"ID рассылки: #{draft.id}\n\n"
        "Прогресс можно смотреть в разделе 'Активные рассылки'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Активные рассылки", callback_data="broadcast_active")],
            [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="broadcast_main")]
        ])
    )


@router.callback_query(F.data == "broadcast_active")
async def broadcast_active_list(callback: CallbackQuery):
    """Список активных рассылок"""


    async with SessionLocal() as session:
        result = await session.execute(
            select(BroadcastTask).where(
                BroadcastTask.status.in_(["pending", "sending"])
            ).order_by(BroadcastTask.created_at.desc())
        )
        tasks = result.scalars().all()

    if not tasks:
        await callback.message.edit_text(
            "📊 Активные рассылки\n\n"
            "Нет активных рассылок.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
            ])
        )
        return

    await callback.message.edit_text(
        f"📊 Активные рассылки\n\nНайдено: {len(tasks)}",
        reply_markup=broadcast_active_kb(tasks)
    )

#
# @router.callback_query(F.data.startswith("broadcast_info_"))
# async def broadcast_info(callback: CallbackQuery):
#     """Информация о конкретной рассылке"""
#     task_id = int(callback.data.replace("broadcast_info_", ""))
#
#     from bot.models.broadcast_task import BroadcastTask
#     from sqlalchemy import select
#
#     async with SessionLocal() as session:
#         result = await session.execute(select(BroadcastTask).where(BroadcastTask.id == task_id))
#         task = result.scalar_one_or_none()
#
#     if not task:
#         await callback.answer("Рассылка не найдена!")
#         return
#
#     status_icons = {
#         "pending": "⏳", "sending": "🟢",
#         "stopped": "🛑", "done": "✅", "draft": "📝"
#     }
#
#     progress = f"{task.sent}/{task.total}" if task.total > 0 else "0/0"
#     percentage = (task.sent / task.total * 100) if task.total > 0 else 0
#
#     info_text = (
#         f"📋 Информация о рассылке #{task.id}\n\n"
#         f"📊 Статус: {status_icons.get(task.status, '❓')} {task.status}\n"
#         f"📈 Прогресс: {progress} ({percentage:.1f}%)\n"
#         f"❌ Ошибки: {task.failed}\n"
#         f"📝 Тип: {task.content_type}\n"
#         f"🕒 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
#         f"🔘 Кнопок: {len(task.buttons)}"
#     )
#
#     await callback.message.edit_text(
#         info_text,
#         reply_markup=broadcast_control_kb(task.id)
#     )

@router.callback_query(F.data.startswith("broadcast_info_"))
async def broadcast_info(callback: CallbackQuery):
    """Информация о конкретной рассылке"""
    task_id = int(callback.data.replace("broadcast_info_", ""))



    async with SessionLocal() as session:
        result = await session.execute(select(BroadcastTask).where(BroadcastTask.id == task_id))
        task = result.scalar_one_or_none()

    if not task:
        await callback.answer("Рассылка не найдена!")
        return

    status_icons = {
        "pending": "⏳", "sending": "🚀",
        "stopped": "🛑", "done": "✅", "draft": "📝"
    }

    # Базовая информация
    info_lines = [
        f"📋 <b>Информация о рассылке #{task.id}</b>\n",
        f"📊 <b>Статус:</b> {status_icons.get(task.status, '❓')} {task.status}",
    ]

    # Прогресс и статистика
    if task.total > 0:
        percent = ((task.sent + task.failed) / task.total) * 100
        progress = progress_bar(task.sent + task.failed, task.total)
        info_lines.append(
            f"📈 <b>Прогресс:</b> {progress} <b>{task.sent + task.failed}/{task.total}</b> ({percent:.1f}%)"
        )
    else:
        info_lines.append("📈 <b>Прогресс:</b> нет данных (0/0)")

    info_lines.append(f"✅ <b>Успешно:</b> {task.sent}")
    info_lines.append(f"❌ <b>Ошибки:</b> {task.failed}")

    if task.total > 0:
        success_rate = (task.sent / task.total) * 100
        error_rate = (task.failed / task.total) * 100
        info_lines.append(f"📊 <b>Успех:</b> {success_rate:.1f}% | <b>Ошибки:</b> {error_rate:.1f}%")

    # Дополнительные параметры рассылки
    info_lines.append(f"🕒 <b>Создана:</b> {task.created_at.strftime('%d.%m.%Y %H:%M')}")

    # Время работы и скорость
    now = datetime.now(timezone.utc)
    elapsed = now - task.created_at
    elapsed_str = format_time_delta(elapsed)

    if task.status in ("sending", "done", "stopped"):
        info_lines.append(f"⏱️ <b>Время работы:</b> {elapsed_str}")

    # Скорость и оставшееся время только для активной рассылки
    if task.status == "sending" and task.sent + task.failed > 0 and elapsed.total_seconds() > 0:
        minutes_passed = elapsed.total_seconds() / 60
        speed = (task.sent + task.failed) / minutes_passed  # сообщений в минуту
        remaining = task.total - (task.sent + task.failed)
        if speed > 0:
            remaining_minutes = remaining / speed
            remaining_delta = timedelta(minutes=remaining_minutes)
            remaining_str = format_time_delta(remaining_delta)
        else:
            remaining_str = "∞"

        info_lines.append(f"⚡ <b>Средняя скорость:</b> {speed:.1f} сообщ/мин")
        info_lines.append(f"⏳ <b>Осталось примерно:</b> {remaining_str}")

    elif task.status in ("done", "stopped") and task.sent > 0 and elapsed.total_seconds() > 0:
        minutes_passed = elapsed.total_seconds() / 60
        speed = (task.sent + task.failed) / minutes_passed
        info_lines.append(f"⚡ <b>Средняя скорость:</b> {speed:.1f} сообщ/мин (с учётом простоя)")

    # Финальные пометки
    if task.status == "done":
        info_lines.append("✅ <b>Рассылка завершена</b>")
    elif task.status == "stopped":
        info_lines.append("🛑 <b>Рассылка остановлена</b>")

    info_text = "\n".join(info_lines)

    await callback.message.edit_text(
        info_text,
        reply_markup=broadcast_control_kb(task.id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("stop_broadcast_"))
async def stop_broadcast(callback: CallbackQuery):
    """Остановка рассылки"""
    task_id = int(callback.data.replace("stop_broadcast_", ""))


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
            "📜 История рассылок\n\n"
            "Нет завершенных рассылок.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
            ])
        )
        return

    history_text = "📜 История рассылок\n\n"
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



# Навигационные обработчики
@router.callback_query(F.data == "back_constructor")
async def back_to_constructor(callback: CallbackQuery):
    """Возврат в конструктор"""
    await broadcast_constructor(callback)


@router.callback_query(F.data == "back_buttons_management")
async def back_to_buttons_management(callback: CallbackQuery):
    """Возврат к управлению кнопками"""
    await callback.message.edit_text(
        "🔘 Управление кнопками",
        reply_markup=buttons_management_kb()
    )


@router.callback_query(F.data == "stop_all_broadcasts")
async def stop_all_broadcasts(callback: CallbackQuery):
    """Остановка всех рассылок"""


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


@router.callback_query(F.data == "forward_post")
async def forward_post_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in BroadcastService.current_editing:
        await callback.answer("Сначала создайте черновик через конструктор!")
        return
    await state.set_state(BroadcastStates.waiting_forward)
    await callback.message.edit_text(
        "📤 Перешлите мне сообщение с готовым постом\n\n"
        "Я скопирую текст и медиа, а кнопки можно будет добавить позже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_constructor")]
        ])
    )

