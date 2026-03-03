from datetime import datetime, timedelta
import math


def format_time_delta(delta: timedelta) -> str:
    """Форматирует timedelta в строку вида 'X дн Y ч Z мин' с правильными склонениями"""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0 мин"

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} " + decline_word(days, "день", "дня", "дней"))
    if hours > 0:
        parts.append(f"{hours} " + decline_word(hours, "час", "часа", "часов"))
    if minutes > 0 or not parts:
        parts.append(f"{minutes} " + decline_word(minutes, "минута", "минуты", "минут"))

    return " ".join(parts)


def decline_word(number: int, one: str, few: str, many: str) -> str:
    """Возвращает правильную форму слова для числа"""
    if number % 10 == 1 and number % 100 != 11:
        return one
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return few
    else:
        return many


def progress_bar(current: int, total: int, length: int = 15) -> str:
    """Генерирует текстовый прогресс-бар"""
    if total == 0:
        return "▱" * length
    filled = math.ceil(current / total * length)
    return "▰" * filled + "▱" * (length - filled)