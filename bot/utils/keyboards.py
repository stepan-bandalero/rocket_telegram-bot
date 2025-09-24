from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.channels import Channel
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



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
            [InlineKeyboardButton(text="➕ Создать рассылку", callback_data="broadcast_create")],
            [InlineKeyboardButton(text="📊 Статус рассылок", callback_data="broadcast_status")],
            [InlineKeyboardButton(text="🛑 Остановить рассылку", callback_data="broadcast_stop")],
            [InlineKeyboardButton(text="📜 История рассылок", callback_data="broadcast_history")],
        ]
    )


def broadcast_type_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Текст", callback_data="broadcast_type_text"),
                InlineKeyboardButton(text="📷 Фото", callback_data="broadcast_type_photo")
            ],
            [
                InlineKeyboardButton(text="🎥 Видео", callback_data="broadcast_type_video"),
                InlineKeyboardButton(text="📹 Кружок", callback_data="broadcast_type_video_note")
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="broadcast_main")]
        ]
    )
