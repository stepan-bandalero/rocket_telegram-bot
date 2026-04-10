

# utils/formatter.py
from aiogram.types import MessageEntity
from aiogram.utils.text_decorations import HtmlDecoration
from typing import Optional


class TelegramFormatter:
    @staticmethod
    def prepare_message_text(message_text: str, entities: list[MessageEntity]) -> tuple[str, Optional[str]]:
        """Используем встроенный декор HTML от aiogram"""
        if not entities:
            return message_text, None

        # Используем встроенный HTML декор aiogram
        decorator = HtmlDecoration()
        html_text = decorator.unparse(message_text, entities)
        return html_text, "HTML"

    @staticmethod
    def prepare_caption_text(message_caption: str, caption_entities: list[MessageEntity]) -> tuple[str, Optional[str]]:
        """То же самое для подписей"""
        if not caption_entities:
            return message_caption, None

        decorator = HtmlDecoration()
        html_text = decorator.unparse(message_caption, caption_entities)
        return html_text, "HTML"

