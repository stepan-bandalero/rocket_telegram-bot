# handlers/admin_mines.py (или в любом вашем роутере)
import json
import re
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message
from redis.asyncio import Redis
from aiogram.filters import Command

from config import settings  # ваши настройки

router = Router()

# Подключаем Redis (настройки возьмите из переменных окружения / settings)
redis_client = Redis.from_url(
    "redis://127.0.0.1:6379",
    decode_responses=True,
)


def format_mines_grid(grid_size: int, mines: list[int], opened: Optional[list[int]] = None) -> str:
    """
    Возвращает текстовое представление сетки с минами.
    Если передан список opened, такие клетки помечаются '🟢', иначе '⬜️'.
    Мины — '💣'.
    Также можно показывать индексы клеток в углу (опционально).
    """
    opened = opened or []
    rows = []
    for row in range(grid_size):
        row_cells = []
        for col in range(grid_size):
            idx = row * grid_size + col
            if idx in mines:
                cell = "💣"
            elif idx in opened:
                cell = "🟢"
            else:
                cell = "⬜️"
            row_cells.append(cell)
        rows.append("".join(row_cells))
    return "\n".join(rows)


@router.message(Command("mine"))
async def cmd_mine(message: Message):
    # Проверка на админа
    if message.from_user.id not in settings.admins:
        return

    # Парсинг user_id
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "❌ Использование: <code>/mine &lt;ID пользователя&gt;</code>",
            parse_mode="HTML",
        )
        return

    user_id_str = parts[1]
    if not user_id_str.isdigit():
        await message.answer("❌ ID должен быть числом.")
        return

    user_id = user_id_str  # в Redis ключи строковые

    # 1. Ищем активную сессию пользователя
    game_key = f"mines:user:{user_id}"
    session_id = await redis_client.get(game_key)

    if not session_id:
        await message.answer(f"ℹ️ У пользователя <code>{user_id}</code> нет активной игры Mines.", parse_mode="HTML")
        return

    # 2. Получаем данные сессии
    raw_session = await redis_client.get(f"mines:{session_id}")
    if not raw_session:
        await message.answer("❌ Данные сессии устарели (ключ не найден).")
        return

    try:
        game = json.loads(raw_session)
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка чтения данных сессии.")
        return

    # 3. Собираем информацию
    grid_size = game["gridSize"]
    mines = game["mines"]
    opened = game.get("opened", [])
    safe_hits = game.get("safeHits", 0)
    mines_count = game.get("minesCount", len(mines))
    bet = game.get("bet", 0)
    currency = game.get("currency", "?")
    server_seed_hash = game.get("serverSeedHash", "—")
    client_seed = game.get("clientSeed", "—")
    nonce = game.get("nonce", "—")
    status = game.get("status", "—")

    # 4. Формируем текстовый вывод
    info_lines = [
        f"🎮 <b>Активная игра Mines</b>",
        f"👤 Пользователь: <code>{user_id}</code>",
        f"🆔 Сессия: <code>{session_id}</code>",
        f"💰 Ставка: {bet} {currency}",
        f"📐 Сетка: {grid_size}×{grid_size}",
        f"💣 Мин: {mines_count}",
        f"🟢 Открыто клеток: {safe_hits}",
        f"📊 Статус: {status}",
        f"🔒 Server seed hash: <code>{server_seed_hash[:16]}...</code>",
        f"🎲 Client seed: <code>{client_seed[:8]}...</code>",
        f"🔢 Nonce: {nonce}",
        "",
        "<b>Поле (мины показаны):</b>",
        f"<pre>{format_mines_grid(grid_size, mines, opened)}</pre>",
        "",
        "Индексы мин: " + " ".join(f"<code>{i + 1}</code>" for i in sorted(mines)),
    ]

    await message.answer("\n".join(info_lines), parse_mode="HTML")