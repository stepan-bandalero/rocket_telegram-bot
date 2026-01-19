from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
import time

from bot.models.users import User
from bot.models.star_invoice import StarsInvoice
from bot.models.promo import PromoLink
from bot.models.promo import PromoReferral
from bot.models.referral_earnings import ReferralEarning
from bot.db import SessionLocal
from bot.config import settings

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

    prices = [LabeledPrice(label=f"{amount} ⭐", amount=amount)]  # Telegram требует целое число
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

async def process_referral_earning(
        session: AsyncSession,
        user_id: int,
        amount: int,
        source_type: str = "stars_payment"
):
    """
    Обработка реферальных начислений
    """
    referrer_id = None
    referral_percentage = 10  # default 10%

    # 1. Проверяем промо-рефералы
    promo_stmt = select(PromoReferral).join(
        PromoLink, PromoLink.id == PromoReferral.promo_id
    ).where(
        PromoReferral.user_id == user_id
    ).limit(1)

    promo_result = await session.execute(promo_stmt)
    promo_referral = promo_result.scalar_one_or_none()

    if promo_referral:
        referrer_id = promo_referral.promo.created_by
        referral_percentage = promo_referral.promo.referral_percentage or 40
    else:
        # 2. Проверяем обычные рефералы через поле referred_by
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user and user.referred_by:
            referrer_id = user.referred_by

    # 3. Если нашли реферера - начисляем бонус
    if referrer_id:
        # Вычисляем сумму бонуса
        referral_amount = (amount * referral_percentage) // 100

        if referral_amount > 0:
            # Обновляем баланс реферера
            referrer_stmt = select(User).where(User.telegram_id == referrer_id)
            referrer_result = await session.execute(referrer_stmt)
            referrer = referrer_result.scalar_one_or_none()

            if referrer:
                # Начисляем звезды рефереру
                referrer.stars_balance = (referrer.stars_balance or 0) + referral_amount

                # Создаем запись о начислении
                referral_earning = ReferralEarning(
                    referrer_id=referrer_id,
                    referred_user_id=user_id,
                    amount=referral_amount,
                    source_type=source_type,
                    source_id=amount  # можно сохранить сумму исходной транзакции
                )
                session.add(referral_earning)

                # Сохраняем изменения
                await session.flush()

                return {
                    "referrer_id": referrer_id,
                    "referral_amount": referral_amount,
                    "referral_percentage": referral_percentage
                }

    return None


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout: PreCheckoutQuery):

    async with SessionLocal() as session:
        stmt = select(StarsInvoice).where(StarsInvoice.payload == pre_checkout.invoice_payload)
        result = await session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            await pre_checkout.answer(ok=False, error_message="Invoice не найден или уже обработан")
            return

        await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message):
    """Telegram подтвердил оплату Stars"""
    payload = message.successful_payment.invoice_payload
    telegram_id = message.from_user.id

    async with SessionLocal() as session:
        # Получаем инвойс
        stmt = select(StarsInvoice).where(StarsInvoice.payload == payload)
        result = await session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice or invoice.status != "pending":
            return

        # Получаем пользователя
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            return

        # Начисляем звезды пользователю
        user.stars_balance = (user.stars_balance or 0) + invoice.amount
        invoice.status = "paid"
        invoice.processed_at = func.now()

        # Обрабатываем реферальные начисления
        referral_result = await process_referral_earning(
            session=session,
            user_id=telegram_id,
            amount=invoice.amount,
            source_type="ton_deposit"
        )

        # Сохраняем все изменения
        await session.commit()
        print(f"Начислено {invoice.amount} ⭐ пользователю {telegram_id}")

        if referral_result:
            print(
                f"Реферальное начисление: "
                f"реферер {referral_result['referrer_id']} получил "
                f"{referral_result['referral_amount']} ⭐ "
                f"({referral_result['referral_percentage']}%)"
            )


    await message.answer(f"✅ Оплата успешна! Вам начислено {invoice.amount} ⭐")