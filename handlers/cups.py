import time
from datetime import datetime, timezone, timedelta

import aiohttp

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Bot

from config import settings
from db import SessionLocal
from services.cups import CupsAnalyticsService

router = Router()
HEALTH_URL = "https://rocket-app.link/cups/health"
MOSCOW_TZ = timezone(timedelta(hours=3))


# --- Форматирование чисел и дат (без изменений) ---
def fmt(n: float | int) -> str:
    if n is None:
        return "—"
    return f"{n:,.0f}".replace(",", " ")

money = fmt

def pct(n: float) -> str:
    if n is None:
        return "—%"
    return f"{n:.1f}%"

def ms(n: float) -> str:
    if n is None:
        return "— мс"
    return f"{n:.0f} мс"

def format_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "")).replace(tzinfo=timezone.utc)
        return dt.astimezone(MOSCOW_TZ).strftime("%d.%m %H:%M")
    except:
        return ts

def format_top_wins(top_wins: list[dict], with_gift: bool = False) -> str:
    """Возвращает HTML-строку с топ‑5 выигрышей в виде дерева."""
    if not top_wins:
        return ""

    lines = []
    for i, win in enumerate(top_wins, 1):
        uid = str(win.get('user_id', ''))
        name = win.get('username') or '—'
        currency = win.get('currency', '')
        bet = money(win.get('bet', 0))
        payout = money(win.get('payout', 0))
        time_str = format_time(win.get('created_at', ''))

        gift_line = ""
        if with_gift and win.get('gift_id'):
            gift_line = f"├ 🎁: {win['gift_id']}\n"

        lines.append(
            f"<b>#{i}</b>\n"
            f"├ ID: <code>{uid}</code>\n"
            f"├ User: @{name}\n"
            f"├ Win: {payout} {currency}\n"
            f"├ Bet: {bet} {currency}\n"
            f"{gift_line}"
            f"└ Time: {time_str}"
        )

    return (
        "<b>🏆 Топ-5 выигрышей сегодня</b>\n"
        + "\n\n".join(lines)
    )

def format_section(title: str, rows: list[tuple[str, str]]) -> str:
    if not rows:
        return f"<b>{title}</b>\n<pre>(нет данных)</pre>"
    max_label = max(len(label) for label, _ in rows)
    max_value = max(len(value) for _, value in rows)
    line_width = max_label + 3 + max_value
    divider = "─" * line_width
    lines = [f"{label:<{max_label}} │ {value}" for label, value in rows]
    return f"<b>{title}</b>\n<pre>{divider}\n" + "\n".join(lines) + "</pre>"


async def get_health():
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
# Команда /cups
# ------------------------------------------------------------
@router.message(Command("cups"))
async def cmd_cups(message: Message, bot: Bot):
    if message.from_user.id not in settings.admins:
        return

    health, latency = await get_health()

    async with SessionLocal() as session:
        service = CupsAnalyticsService(session)
        all_time = await service.global_stats()

        msk_midnight = datetime.now(MOSCOW_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        utc_start = msk_midnight.astimezone(timezone.utc).replace(tzinfo=None)
        today = await service.today_stats(utc_start)

    if not health:
        await message.answer("🔴 Cups engine offline")
        return

    # --- Блок 1: Состояние сервера ---
    mem = health.get("memory", {})
    rss_mb = mem.get("rss", 0) // 1024 // 1024

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
        ("", ""),
        ("Средние показатели", ""),
        ("• Ставка", money(all_time['avg_bet'])),
        ("• Выплата", money(all_time['avg_payout'])),
        ("", ""),
        ("Рекорды", ""),
        ("• Max win", money(all_time['max_win'])),
    ]
    all_time_block = format_section("📊 За всё время", all_time_rows)

    # --- Блок 3: Сегодняшняя статистика ---
    # --- Сегодняшняя статистика (без топа) ---
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
        ("", ""),
        ("Рекорды", ""),
        ("• Max win", money(today['max_win'])),
    ]
    today_block = format_section("📅 Сегодня (МСК)", today_rows)

    # --- Топ-5 с gift_id ---
    top_block = format_top_wins(today.get('top_wins', []), with_gift=True)

    full_message = f"{server_block}\n\n{all_time_block}\n\n{today_block}"
    if top_block:
        full_message += f"\n\n{top_block}"

    await message.answer(full_message, parse_mode="HTML")