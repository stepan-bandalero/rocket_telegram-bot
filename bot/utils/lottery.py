import asyncio
import re

from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime

from bot.db import SessionLocal
from bot.models.gift_catalog import GiftCatalog
from zoneinfo import ZoneInfo

# Настройка Jinja2
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))




def format_time_left(results_date_str: str) -> str:
    """
    Принимает строку с датой в формате 'ДД.ММ.ГГГГ ЧЧ:ММ'
    Возвращает строку вида '1 день 12:34:56' или '12:34:56', если дней нет.
    """
    try:
        # Парсим строку (пример: "01.03.2026 15:00")
        match = re.match(r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', results_date_str)
        if not match:
            return "Неверный формат даты"
        day, month, year, hour, minute = map(int, match.groups())
        target = datetime(year, month, day, hour, minute)
        now = datetime.now()
        diff = target - now
        if diff.total_seconds() <= 0:
            return "Розыгрыш завершён"

        days = diff.days
        seconds = diff.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        # Склонение слова "день" (можно упростить)
        if days == 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        elif days == 1:
            return f"1 день {hours:02d}:{minutes:02d}:{secs:02d}"
        elif 2 <= days <= 4:
            return f"{days} дня {hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{days} дней {hours:02d}:{minutes:02d}:{secs:02d}"
    except Exception as e:
        return f"Ошибка: {e}"

async def generate_lottery_preview(data: dict) -> bytes:
    prize_gift_id = data.get("prize_gift_id")
    async with SessionLocal() as session:
        gift = await session.get(GiftCatalog, prize_gift_id)
        if gift:
            gift_price_cents = gift.price_cents
        else:
            gift_price_cents = 1000               # заглушка, если приз не найден

    # Расчёт оставшегося времени
    results_date_iso = data.get("results_date")
    tz = ZoneInfo("Europe/Moscow")                # часовой пояс бота
    now = datetime.now(tz)
    try:
        target = datetime.fromisoformat(results_date_iso)
        if target.tzinfo is None:
            target = target.replace(tzinfo=tz)
        diff = target - now
        if diff.total_seconds() <= 0:
            time_left = "Розыгрыш завершён"
        else:
            days = diff.days
            seconds = diff.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            if days == 0:
                time_left = f"{hours:02d}:{minutes:02d}:{secs:02d}"
            elif days == 1:
                time_left = f"1 день {hours:02d}:{minutes:02d}:{secs:02d}"
            elif 2 <= days <= 4:
                time_left = f"{days} дня {hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                time_left = f"{days} дней {hours:02d}:{minutes:02d}:{secs:02d}"
    except Exception:
        time_left = "Неверная дата"

    preview_data = {
        "title": data.get("title", "Лотерея"),
        "description": data.get("description", ""),
        "type": data.get("type", "paid"),
        "ticket_price_stars": data.get("ticket_price_stars", 0),
        "prize_gift_id": prize_gift_id,
        "winners_count": data.get("winners_count", 1),
        "time_left": time_left,
        "max_tickets_per_user": data.get("max_tickets_per_user"),
        "max_total_tickets": data.get("max_total_tickets"),
        "user_tickets_count": 0,
        "participants_count": 0,
        "tickets_sold_count": 0,
        "gift_price_cents": gift_price_cents,
        "gift_price_stars": gift_price_cents / 100,
    }

    template = env.get_template("lottery_preview.html")
    html_content = template.render(preview_data)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 400, "height": 600})
        await page.set_content(html_content, wait_until="networkidle")
        await asyncio.sleep(0.5)
        screenshot = await page.locator("body").screenshot()
        await browser.close()
        return screenshot
