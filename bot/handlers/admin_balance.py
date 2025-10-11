from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.config import settings
from bot.db import SessionLocal
from bot.models.users import User
from bot.models.user_transaction import UserTransaction  # ✅ модель транзакций
import re

router = Router()


@router.message(F.text.startswith("/manage_balance"))
async def manage_balance(message: Message):
    if message.from_user.id not in settings.admins:
        return

    parts = message.text.split()
    if len(parts) != 4:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Использование:\n"
            "<code>/manage_balance &lt;ID&gt; &lt; +/-/= &gt; &lt;Сумма&gt;</code>",
            parse_mode="HTML",
        )
        return

    _, user_id_str, operator, amount_str = parts

    # Проверка ID
    if not user_id_str.isdigit():
        await message.answer("❌ ID должен быть числом.")
        return

    user_id = int(user_id_str)

    # Проверка оператора
    if operator not in ["+", "-", "="]:
        await message.answer("❌ Оператор должен быть одним из: +  -  =")
        return

    # Проверка суммы
    if not re.match(r"^\d+$", amount_str):
        await message.answer("❌ Сумма должна быть положительным числом.")
        return

    amount = int(amount_str)
    if amount < 0:
        await message.answer("❌ Сумма должна быть больше 0.")
        return

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer(f"❌ Пользователь с ID <code>{user_id}</code> не найден.", parse_mode="HTML")
            return

        old_balance = user.ton_balance or 0

        # Обновляем баланс
        if operator == "+":
            new_balance = old_balance + amount
        elif operator == "-":
            if old_balance < amount:
                await message.answer(
                    f"❌ Недостаточно средств. Баланс пользователя: <b>{old_balance}</b> TON.",
                    parse_mode="HTML",
                )
                return
            new_balance = old_balance - amount
        else:  # "="
            new_balance = amount

        user.ton_balance = new_balance


        await session.commit()

    await message.answer(
        f"✅ Баланс обновлён!\n\n"
        f"👤 Пользователь: <code>{user_id}</code>\n"
        f"💰 Было: <b>{old_balance}</b>\n"
        f"🔄 Стало: <b>{new_balance}</b>\n"
        f"✍️ Операция: {operator} {amount}",
        parse_mode="HTML",
    )
