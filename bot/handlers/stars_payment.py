from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.users import User
from bot.models.star_invoice import StarsInvoice
from bot.db import SessionLocal
from bot.config import settings

from sqlalchemy import func
import time

router = Router()



@router.message(F.text.startswith("/pay_stars"))
async def create_invoice(message: Message):
    if message.from_user.id not in settings.admins:
        return
    """Создание invoice для Telegram Stars"""
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit() or int(parts[1]) < 1:
        await message.reply("❌ Использование: /pay_stars <кол-во звезд>")
        return

    amount = int(parts[1])
    telegram_id = message.from_user.id
    payload = f"{telegram_id}-{amount}-{int(time.time() * 1000)}"  # уникальный payload

    async with SessionLocal() as session:
        invoice = StarsInvoice(payload=payload, telegram_id=telegram_id, amount=amount, status="pending")
        session.add(invoice)
        await session.commit()

    prices = [LabeledPrice(label=f"{amount} ⭐", amount=amount * 100)]  # Telegram требует целое число
    start_parameter = f"stars-{payload}"

    # Отправка invoice через Telegram
    await message.bot.send_invoice(
        chat_id=telegram_id,
        title="Пополнение Stars",
        description=f"Начисление {amount} ⭐ на баланс",
        payload=payload,
        currency="XTR",  # обязательно внутренняя валюта
        prices=prices,
        start_parameter=start_parameter
    )



@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout: PreCheckoutQuery):
    """Обработка pre_checkout"""
    async with SessionLocal() as session:
        stmt = select(StarsInvoice).where(StarsInvoice.payload == pre_checkout.invoice_payload)
        result = await session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            await pre_checkout.answer(ok=False, error_message="Invoice не найден или уже обработан")
            return

        await pre_checkout.answer(ok=True)


@router.message(F.successful_payment())
async def handle_successful_payment(message: Message):
    """Telegram подтвердил оплату Stars"""
    payload = message.successful_payment.invoice_payload
    telegram_id = message.from_user.id

    async with SessionLocal() as session:
        stmt = select(StarsInvoice).where(StarsInvoice.payload == payload)
        result = await session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            return  # Уже обработан или нет записи

        # Начисляем звезды пользователю
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            return  # Пользователь не найден

        # Начисляем
        user.stars_balance = (user.stars_balance or 0) + invoice.amount
        invoice.status = "paid"
        invoice.processed_at = func.now()
        await session.commit()

    await message.answer(f"✅ Оплата успешна! Вам начислено {invoice.amount} ⭐")
