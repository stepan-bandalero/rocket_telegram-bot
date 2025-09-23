from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models.channels import Channel


def get_subscription_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=ch.title, url=ch.url)]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
