# handlers/mines.py (финальная версия — минималистичные таблицы)

import time
from datetime import datetime, timezone, timedelta

import aiohttp

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Bot

from config import settings
from db import SessionLocal
from services.mines import MinesAnalyticsService

router = Router()
HEALTH_URL = "https://rocket-app.link/mines/health"
MOSCOW_TZ = timezone(timedelta(hours=3))


# ------------------------------------------------------------
# Форматирование чисел
# ------------------------------------------------------------

def fmt(n: float | int) -> str:
    """Красивый вывод: 1234567 → 1 234 567"""
    if n is None:
        return "—"
    return f"{n:,.0f}".replace(",", " ")


def money(n: float | int) -> str:
    return fmt(n)


def pct(n: float) -> str:
    if n is None:
        return "—%"
    return f"{n:.1f}%"


def ms(n: float) -> str:
    if n is None:
        return "— мс"
    return f"{n:.0f} мс"


def format_time(ts: str) -> str:
    """Дата из ISO в московское время"""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=timezone.utc)
        return dt.astimezone(MOSCOW_TZ).strftime("%d.%m %H:%M")
    except:
        return ts


# ------------------------------------------------------------
# Построитель секций
# ------------------------------------------------------------

def format_section(title: str, rows: list[tuple[str, str]]) -> str:
    """
    Превращает заголовок и список (название, значение) в красивый блок
    с моноширинным шрифтом и вертикальной чертой-разделителем.
    """
    if not rows:
        return f"<b>{title}</b>\n<pre>(нет данных)</pre>"

    # Максимальная ширина левой колонки
    max_label = max(len(label) for label, _ in rows)
    # Максимальная ширина правой колонки (для вычисления длины разделителя)
    max_value = max(len(value) for _, value in rows)

    # Общая ширина строки (левая + пробелы + разделитель + правая)
    line_width = max_label + 3 + max_value

    # Горизонтальная черта под заголовком
    divider = "─" * line_width

    # Строки с идеально ровной вертикальной чертой
    lines = [
        f"{label:<{max_label}} │ {value}"
        for label, value in rows
    ]

    return f"<b>{title}</b>\n<pre>{divider}\n" + "\n".join(lines) + "</pre>"


async def get_health():
    """Проверка движка Mines"""
    try:
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.get(HEALTH_URL, timeout=5) as r:
                latency = (time.time() - start) * 1000
                if r.status == 200:
                    return await r.json(), latency
    except:
        pass
    return None, 0


# ------------------------------------------------------------
# Команда /mines
# ------------------------------------------------------------

@router.message(Command("mines"))
async def cmd_mines(message: Message, bot: Bot):
    if message.from_user.id not in settings.admins:
        return

    health, latency = await get_health()

    async with SessionLocal() as session:
        service = MinesAnalyticsService(session)
        all_time = await service.global_stats()

        # Сегодня с 00:00 по Москве
        msk_midnight = datetime.now(MOSCOW_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        utc_start = msk_midnight.astimezone(timezone.utc).replace(tzinfo=None)
        today = await service.today_stats(utc_start)

    # --- Если движок не отвечает ---
    if not health:
        await message.answer("🔴 Mines engine offline")
        return

    # --- Блок 1: Состояние сервера ---
    mem = health.get("memory", {})
    rss_mb = mem.get("rss", 0) // 1024 // 1024
    heap_mb = mem.get("heapUsed", 0) // 1024 // 1024

    server_rows = [
        ("🟢 Доступен", f"ping {ms(latency)}"),
        ("🕒 Обновлено", format_time(health.get('timestamp', ''))),
        ("🗄 Redis", "✅" if health.get('redis') else "❌"),
        ("🗄 Postgres", "✅" if health.get('postgres') else "❌"),
        ("👥 Онлайн", str(health.get('online', 0))),
        ("🎮 Активных игр", str(health.get('activeGames', 0))),
        ("💾 Память (RSS)", f"{rss_mb} МБ"),
    ]
    server_block = format_section("🖥 Состояние сервера", server_rows)

    # --- Блок 2: Общая статистика за всё время ---
    all_time_rows = [
        ("👤 Игроков", fmt(all_time['users'])),
        ("🎲 Игр", fmt(all_time['games'])),
        ("💰 Сумма ставок", money(all_time['bets'])),
        ("💸 Выплачено", money(all_time['payout'])),
        ("📈 Доход", money(all_time['pnl'])),
        ("🏆 Выигрышей", pct(all_time['winrate'])),
        ("📊 RTP", pct(all_time['rtp'])),
        ("", ""),  # пустая строка-разделитель
        ("Средние показатели", ""),
        ("• Ставка", money(all_time['avg_bet'])),
        ("• Выплата", money(all_time['avg_payout'])),
        ("• Открыто", f"{all_time['avg_safe_hits']:.1f}"),
        ("• Мины", f"{all_time['avg_mines']:.1f}"),
        ("• Поле", f"{all_time['avg_grid']:.1f}"),
        ("", ""),
        ("Рекорды", ""),
        ("• Max win", money(all_time['max_win'])),
        ("• Max bet", money(all_time['max_bet'])),
        ("• Max X", f"x{all_time['max_multiplier']:.2f}"),
        ("• Avg X", f"x{all_time['avg_multiplier']:.2f}"),
    ]
    all_time_block = format_section("📊 За всё время", all_time_rows)

    # --- Блок 3: Сегодняшняя статистика ---
    today_rows = [
        ("👤 Игроков", fmt(today['users'])),
        ("🎲 Игр", fmt(today['games'])),
        ("💰 Сумма ставок", money(today['bets'])),
        ("💸 Выплачено", money(today['payout'])),
        ("📈 Доход", money(today['pnl'])),
        ("🏆 Выигрышей", pct(today['winrate'])),
        ("📊 RTP", pct(today['rtp'])),
        ("", ""),
        ("Средние показатели", ""),
        ("• Ставка", money(today['avg_bet'])),
        ("• Выплата", money(today['avg_payout'])),
        ("• Открыто", f"{today['avg_safe_hits']:.1f}"),
        ("• Мины", f"{today['avg_mines']:.1f}"),
        ("• Поле", f"{today['avg_grid']:.1f}"),
        ("", ""),
        ("Рекорды", ""),
        ("• Max win", money(today['max_win'])),
        ("• Max bet", money(today['max_bet'])),
        ("• Max X", f"x{today['max_multiplier']:.2f}"),
    ]
    today_block = format_section("📅 Сегодня (МСК)", today_rows)

    # --- Сборка итогового сообщения ---
    full_message = f"{server_block}\n\n{all_time_block}\n\n{today_block}"

    await message.answer(full_message, parse_mode="HTML")