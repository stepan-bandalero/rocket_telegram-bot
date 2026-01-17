# # bot/utils/formatter.py
# from aiogram.types import MessageEntity
# from typing import Optional
#
#
# class TelegramFormatter:
#     @staticmethod
#     def entities_to_html(text: str, entities: list[MessageEntity]) -> str:
#         """Преобразует текст с entities в HTML с учётом UTF-16 смещений для эмодзи."""
#         if not entities:
#             return text
#
#         result = []
#         last_pos = 0
#
#         # Преобразуем текст в список символов для удобства работы
#         chars = list(text)
#
#         # Функция для вычисления длины в UTF-16 кодовых единицах
#         def utf16_length(s: str) -> int:
#             return len(s.encode('utf-16-le')) // 2
#
#         # Текущая позиция в UTF-16
#         utf16_offset = 0
#
#         for entity in sorted(entities, key=lambda e: e.offset):
#             # Вычисляем позицию в символах Python, соответствующую UTF-16 offset
#             char_offset = 0
#             current_utf16 = 0
#             while char_offset < len(chars) and current_utf16 < entity.offset:
#                 current_utf16 += utf16_length(chars[char_offset])
#                 char_offset += 1
#
#             # Добавляем текст до entity
#             if last_pos < char_offset:
#                 result.append(''.join(chars[last_pos:char_offset]))
#
#             # Вычисляем длину entity в символах Python
#             char_length = 0
#             entity_utf16_len = 0
#             while (char_offset + char_length < len(chars) and
#                    entity_utf16_len < entity.length):
#                 entity_utf16_len += utf16_length(chars[char_offset + char_length])
#                 char_length += 1
#
#             # Извлекаем форматированный текст
#             formatted_text = ''.join(chars[char_offset:char_offset + char_length])
#
#             # Применяем HTML-теги
#             if entity.type == "bold":
#                 result.append(f"<b>{formatted_text}</b>")
#             elif entity.type == "italic":
#                 result.append(f"<i>{formatted_text}</i>")
#             elif entity.type == "underline":
#                 result.append(f"<u>{formatted_text}</u>")
#             elif entity.type == "strikethrough":
#                 result.append(f"<s>{formatted_text}</s>")
#             elif entity.type == "code":
#                 result.append(f"<code>{formatted_text}</code>")
#             elif entity.type == "pre":
#                 result.append(f"<pre>{formatted_text}</pre>")
#             elif entity.type == "text_link":
#                 result.append(f"<a href=\"{entity.url}\">{formatted_text}</a>")
#             elif entity.type == "blockquote":
#                 result.append(f"<blockquote>{formatted_text}</blockquote>")
#             elif entity.type == "spoiler":
#                 result.append(f"<tg-spoiler>{formatted_text}</tg-spoiler>")
#             elif entity.type in ["mention", "hashtag", "cashtag", "bot_command", "url", "email", "phone_number"]:
#                 result.append(formatted_text)
#
#             # Обновляем позицию в символах Python
#             last_pos = char_offset + char_length
#             utf16_offset = entity.offset + entity.length
#
#         # Добавляем остаток текста
#         if last_pos < len(chars):
#             result.append(''.join(chars[last_pos:]))
#
#         return ''.join(result)
#
#     @staticmethod
#     def prepare_message_text(message_text: str, entities: list[MessageEntity]) -> tuple[str, Optional[str]]:
#         """Основной метод подготовки текста сообщения"""
#         if not entities:
#             return message_text, None
#
#         html_text = TelegramFormatter.entities_to_html(message_text, entities)
#         return html_text, "HTML"
#
#     @staticmethod
#     def prepare_caption_text(message_caption: str, caption_entities: list[MessageEntity]) -> tuple[str, Optional[str]]:
#         """Метод подготовки текста подписи"""
#         if not caption_entities:
#             return message_caption, None
#
#         html_text = TelegramFormatter.entities_to_html(message_caption, caption_entities)
#         return html_text, "HTML"



# bot/utils/formatter.py
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

