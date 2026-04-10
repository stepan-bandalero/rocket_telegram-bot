from aiolimiter import AsyncLimiter
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any
import functools
from collections import defaultdict


class RateLimiterMiddleware(BaseMiddleware):
    """
    Middleware для ограничения скорости отправки сообщений.
    Учитывает:
    1. Глобальный лимит бота (25/сек)
    2. Лимит на пользователя (1/3 сек)
    """

    def __init__(self, rate: int = 25, time_period: int = 1):
        super().__init__()
        # Глобальный лимитер на все отправки бота
        self.global_limiter = AsyncLimiter(rate, time_period)
        # Лимитеры для отдельных чатов (user_id → AsyncLimiter)
        self.user_limiters: Dict[int, AsyncLimiter] = defaultdict(
            lambda: AsyncLimiter(1, 1)  # 1 сообщение в 1 секунду
        )
        self._wrapped_bots: Dict[int, bool] = {}

    async def __call__(
            self,
            handler: Callable,
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        bot = data.get("bot")
        if bot and id(bot) not in self._wrapped_bots:
            await self._wrap_bot_methods(bot)
            self._wrapped_bots[id(bot)] = True

        return await handler(event, data)


    async def _wrap_bot_methods(self, bot):
        """Оборачиваем методы отправки бота в двойной лимитер"""

        methods_to_wrap = [
            'send_message', 'send_photo', 'send_video',
            'send_document', 'send_audio', 'send_video_note',
            'send_media_group', 'copy_message', 'forward_message',
        ]

        for method_name in methods_to_wrap:
            if hasattr(bot, method_name):
                original_method = getattr(bot, method_name)

                @functools.wraps(original_method)
                async def wrapped_method(*args, __original=original_method, **kwargs):
                    # Извлекаем user_id из аргументов
                    user_id = self._extract_user_id(args, kwargs)

                    # 1. Глобальный лимит бота
                    async with self.global_limiter:
                        # 2. Лимит для конкретного пользователя
                        if user_id:
                            user_limiter = self.user_limiters[user_id]
                            async with user_limiter:
                                return await __original(*args, **kwargs)
                        else:
                            return await __original(*args, **kwargs)

                setattr(bot, method_name, wrapped_method)


    def _extract_user_id(self, args, kwargs):
        """Извлекает user_id из аргументов метода отправки"""
        # Позиционные аргументы: send_message(chat_id, text, ...)
        if args and len(args) > 0:
            # Первый аргумент обычно chat_id
            chat_id = args[0]
            if isinstance(chat_id, int):
                return chat_id

        # Именованные аргументы
        if 'chat_id' in kwargs:
            chat_id = kwargs['chat_id']
            if isinstance(chat_id, int):
                return chat_id

        return None