

from __future__ import annotations

from models.channels import Channel
from models.broadcast_task import BroadcastTask
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# =========================
# Подписки
# =========================

def get_subscription_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"📢 {ch.title}",
                url=ch.url,
                style="primary",
            )
        ]
        for ch in channels
    ]

    buttons.append([
        InlineKeyboardButton(
            text="✅ Продолжить",
            callback_data="check_subs",
            style="success",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# Главное меню рассылки
# =========================

def broadcast_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎨 Конструктор рассылки",
                    callback_data="broadcast_constructor",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Активные рассылки",
                    callback_data="broadcast_active",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 История рассылок",
                    callback_data="broadcast_history",
                )
            ],
        ]
    )


# =========================
# Конструктор рассылки
# =========================

def broadcast_constructor_kb(
    task: BroadcastTask,
    is_editing: bool = False,
) -> InlineKeyboardMarkup:

    buttons = []

    if not is_editing:
        buttons.extend([
            [
                InlineKeyboardButton(
                    text="📤 Переслать готовый пост",
                    callback_data="forward_post",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать текст",
                    callback_data="edit_text",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼️ Изменить медиа",
                    callback_data="edit_media",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔘 Управление кнопками",
                    callback_data="edit_buttons",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁️ Предпросмотр",
                    callback_data="preview_broadcast",
                    style="primary",

                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Запустить рассылку",
                    callback_data="start_broadcast",
                    style="success",
                )
            ],
        ])
    else:
        buttons.extend([
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data="save_editing",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="back_constructor",
                    style="danger",
                )
            ],
        ])

    buttons.extend([

        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="broadcast_main",
            )
        ],
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# Управление кнопками
# =========================

def buttons_management_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить кнопку",
                    callback_data="add_button",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Очистить все кнопки",
                    callback_data="clear_buttons",
                    style="danger",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к конструктору",
                    callback_data="back_constructor",
                )
            ],
        ]
    )


# =========================
# Тип кнопки
# =========================

def button_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 URL-кнопка",
                    callback_data="button_type_url",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Web App",
                    callback_data="button_type_webapp",
                    style="primary",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_buttons_management",
                )
            ],
        ]
    )


# =========================
# Активные рассылки
# =========================

def broadcast_active_kb(tasks: list[BroadcastTask]) -> InlineKeyboardMarkup:
    buttons = []

    for task in tasks:
        status_icon = (
            "🟢" if task.status == "sending"
            else "🟡" if task.status == "pending"
            else "🔴"
        )

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} Рассылка #{task.id} ({task.sent + task.failed}/{task.total})",
                callback_data=f"broadcast_info_{task.id}",
                style="primary",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🛑 Остановить все",
            callback_data="stop_all_broadcasts",
            style="danger",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="broadcast_main",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =========================
# Управление конкретной рассылкой
# =========================

def broadcast_control_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛑 Остановить",
                    callback_data=f"stop_broadcast_{task_id}",
                    style="danger",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data="broadcast_active",
                )
            ],
        ]
    )
