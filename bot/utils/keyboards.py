# bot/utils/keyboards.py
from bot.models.channels import Channel
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.broadcast_task import BroadcastTask



def get_subscription_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=ch.title, url=ch.url)]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)





def broadcast_main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Конструктор рассылки", callback_data="broadcast_constructor")],
            [InlineKeyboardButton(text="📊 Активные рассылки", callback_data="broadcast_active")],
            [InlineKeyboardButton(text="📜 История рассылок", callback_data="broadcast_history")],
        ]
    )


def broadcast_constructor_kb(task: BroadcastTask, is_editing: bool = False):
    """Клавиатура конструктора рассылки"""
    buttons = []

    # Кнопки редактирования
    if not is_editing:
        buttons.extend([
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="edit_text")],
            [InlineKeyboardButton(text="🖼️ Изменить медиа", callback_data="edit_media")],
            [InlineKeyboardButton(text="🔘 Управление кнопками", callback_data="edit_buttons")],
            [
                InlineKeyboardButton(text="📷 Текст+Фото", callback_data="set_type_photo"),
                InlineKeyboardButton(text="🎥 Текст+Видео", callback_data="set_type_video")
            ],
            [
                InlineKeyboardButton(text="📹 Кружок", callback_data="set_type_video_note"),
                InlineKeyboardButton(text="📝 Только текст", callback_data="set_type_text")
            ]
        ])
    else:
        # В режиме редактирования показываем кнопки сохранения/отмены
        buttons.append([InlineKeyboardButton(text="✅ Сохранить", callback_data="save_editing")])
        buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_editing")])

    # Основные действия
    buttons.extend([
        [InlineKeyboardButton(text="👁️ Предпросмотр", callback_data="preview_broadcast")],
        [InlineKeyboardButton(text="🚀 Запустить рассылку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="💾 Сохранить черновик", callback_data="save_draft")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def buttons_management_kb():
    """Клавиатура управления кнопками"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="add_button")],
            [InlineKeyboardButton(text="✏️ Редактировать кнопки", callback_data="edit_buttons_list")],
            [InlineKeyboardButton(text="🗑️ Очистить все кнопки", callback_data="clear_buttons")],
            [InlineKeyboardButton(text="⬅️ Назад к конструктору", callback_data="back_constructor")]
        ]
    )


def button_type_kb():
    """Выбор типа кнопки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 URL-кнопка", callback_data="button_type_url")],
            [InlineKeyboardButton(text="⚡ Web App", callback_data="button_type_webapp")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_buttons_management")]
        ]
    )


def broadcast_active_kb(tasks: list[BroadcastTask]):
    """Клавиатура для активных рассылок"""
    buttons = []
    for task in tasks:
        status_icon = "🟢" if task.status == "sending" else "🟡" if task.status == "pending" else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} Рассылка #{task.id} ({task.sent}/{task.total})",
                callback_data=f"broadcast_info_{task.id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🛑 Остановить все", callback_data="stop_all_broadcasts")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def broadcast_control_kb(task_id: int):
    """Клавиатура управления конкретной рассылкой"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Остановить", callback_data=f"stop_broadcast_{task_id}")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_broadcast_{task_id}")],
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="broadcast_active")]
        ]
    )