# bot/handlers/admin/gift_promos.py
from aiogram import Router, F
from aiogram.types import Message
from config import settings
from services.gift_promo import GiftPromoService
from models.gift_catalog import GiftCatalog
from db import SessionLocal
from sqlalchemy import select

router = Router()


@router.message(F.text.startswith("/add_gift_promo"))
async def add_gift_promo(message: Message):
    if message.from_user.id not in settings.admins:
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Использование: /add_gift_promo <gift_id> <max_uses>")
        return

    gift_id, max_uses_str = parts[1], parts[2]
    try:
        max_uses = int(max_uses_str)
        if max_uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Количество использований должно быть положительным числом.")
        return

    async with SessionLocal() as session:
        gift = await session.get(GiftCatalog, gift_id)
        if not gift:
            await message.answer("❌ Подарок не найден.")
            return

        promo = await GiftPromoService.create_promo(session, gift_id, message.from_user.id, max_uses)
        await message.answer(
            f"🎟 Промокод создан!\n\n"
            f"🎁 <b>{gift.title}</b>\n"
            f"🔢 Использований: <b>{max_uses}</b>\n"
            f"🔗 Код: <code>{promo.code}</code>",
            parse_mode="HTML"
        )


@router.message(F.text == "/gift_promos")
async def list_gift_promos(message: Message):
    if message.from_user.id not in settings.admins:
        return

    async with SessionLocal() as session:
        promos = await GiftPromoService.list_promos(session)

    if not promos:
        await message.answer("📭 Промокодов нет.")
        return

    chunks = []
    text = "🎁 <b>Активные промокоды</b>\n\n"

    for promo in promos:
        block = (
            f"🔑 Код: <code>{promo['code']}</code>\n"
            f"🎁 Подарок: {promo['title']}\n"
            f"👤 Создатель: <code>{promo['created_by']}</code>\n"
            f"🧮 Использовано: {promo['uses_count']}/{promo['max_uses']}\n"
            f"📅 Создан: {promo['created_at'].strftime('%Y-%m-%d')}\n"
            f"⏰ Первое: {promo['first_use'] or '—'}\n"
            f"⌛ Последнее: {promo['last_use'] or '—'}\n"
            f"📦 Статус: {'🟢 Активен' if promo['is_active'] else '🔴 Неактивен'}\n\n"
        )
        if len(text) + len(block) > 4000:
            chunks.append(text)
            text = block
        else:
            text += block

    chunks.append(text)
    for chunk in chunks:
        await message.answer(chunk, parse_mode="HTML")
