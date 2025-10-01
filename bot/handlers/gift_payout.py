from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.config import settings
from bot.db import SessionLocal
from bot.models.users import User
from bot.models.user_gift import UserGift, GiftStatus
from bot.models.gift_withdrawals import GiftWithdrawal
from bot.models.bets import Bet
from datetime import datetime

router = Router()

PAGE_SIZE = 1  # 1 заявка на странице


async def get_withdrawals_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE

    # Получаем заявки на вывод со статусом pending или processing
    stmt = (
        select(GiftWithdrawal)
        .join(UserGift, GiftWithdrawal.user_gift_id == UserGift.id)
        .join(User, UserGift.user_id == User.telegram_id)
        .options(
            selectinload(GiftWithdrawal.user_gift_id).selectinload(UserGift.user),
            selectinload(GiftWithdrawal.user_gift_id).selectinload(UserGift.gift_catalog_id)
        )
        .where(GiftWithdrawal.status.in_(["pending", "processing"]))
        .order_by(GiftWithdrawal.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await session.execute(stmt)
    withdrawals = result.scalars().all()

    # Получаем общее количество заявок со статусом pending или processing
    total_stmt = (
        select(func.count(GiftWithdrawal.id))
        .where(GiftWithdrawal.status.in_(["pending", "processing"]))
    )
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one()

    return withdrawals, total_count


async def get_user_recent_bets(session: AsyncSession, user_id: int, limit: int = 5):
    """Получаем последние ставки пользователя"""
    stmt = (
        select(Bet)
        .where(Bet.user_id == user_id)
        .order_by(Bet.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


def build_withdrawals_keyboard(current_page: int, total_pages: int, withdrawal_id: int) -> InlineKeyboardMarkup:
    buttons = []

    # Кнопки пагинации
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"withdraw_page:{current_page - 1}"))

    # Кнопка текущей страницы
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="current_withdraw_page"))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"withdraw_page:{current_page + 1}"))

    # Кнопки действий
    action_buttons = [
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_withdraw:{withdrawal_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw:{withdrawal_id}")
    ]

    keyboard = []
    if buttons:
        keyboard.append(buttons)
    keyboard.append(action_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_bet_line(bet: Bet, index: int) -> str:
    """Форматирование информации о ставке"""
    amount = f"{bet.amount_cents / 100:.2f}" if bet.amount_cents else "0.00"
    win = f"{bet.win_cents / 100:.2f}" if bet.win_cents else "0.00"
    multiplier = f"{bet.cashout_multiplier_bp / 100:.2f}x" if bet.cashout_multiplier_bp else "—"
    status = "✅ Выведена" if bet.cashed_out else "❌ Не выведена"
    asset = "💰 FIAT" if bet.asset_type == "FIAT" else "💎 GIFT"

    return (
        f"┣ #{index} | {asset}\n"
        f"┣ 💰 Ставка: ${amount}\n"
        f"┣ 🎯 Множитель: {multiplier}\n"
        f"┣ 🏆 Выигрыш: ${win}\n"
        f"┗ 📊 Статус: {status}\n"
    )


def format_withdrawal_message(withdrawal: GiftWithdrawal, recent_bets: list, page: int, total_pages: int) -> str:
    """Форматирование сообщения с информацией о заявке"""
    user_gift = withdrawal.user_gift
    user = user_gift.user
    gift_catalog = user_gift.gift_catalog

    # Информация о подарке
    gift_title = gift_catalog.title if gift_catalog else "Неизвестный подарок"
    gift_price = f"{user_gift.price_cents / 100:.2f}" if user_gift.price_cents else "0.00"

    # Информация о пользователе
    username = f"@<code>{user.username}</code>" if user.username else "—"
    user_balance = f"{user.ton_balance / 100:.2f} TON" if user.ton_balance else "0.00 TON"

    # Информация о заявке
    created_at = withdrawal.created_at.strftime("%d.%m.%Y %H:%M") if withdrawal.created_at else "—"

    message_parts = [
        f"📦 <b>ЗАЯВКА НА ВЫВОД ПОДАРКА</b>\n",
        f"📄 Страница: <b>{page}/{total_pages}</b>\n",
        f"⏰ Создана: <b>{created_at}</b>\n",

        f"🎁 <b>ИНФОРМАЦИЯ О ПОДАРКЕ</b>\n",
        f"┣ Название: <b>{gift_title}</b>\n",
        f"┣ Цена: <b>${gift_price}</b>\n",
    ]


    message_parts.extend([
        f"\n👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>\n",
        f"┣ ID: <code>{user.telegram_id}</code>\n",
        f"┣ Имя: <b>{user.first_name or '—'}</b>\n",
        f"┣ Username: {username}\n",
        f"┗ Баланс: <b>{user_balance}</b>\n",
    ])

    # Последние ставки пользователя
    if recent_bets:
        message_parts.append(f"\n🎰 <b>ПОСЛЕДНИЕ СТАВКИ ({len(recent_bets)})</b>\n")
        for i, bet in enumerate(recent_bets, 1):
            message_parts.append(format_bet_line(bet, i))
    else:
        message_parts.append(f"\n🎰 <b>ПОСЛЕДНИЕ СТАВКИ</b>\n┗ <i>Ставок не найдено</i>\n")

    # Дополнительная информация о заявке
    if withdrawal.error_text:
        message_parts.append(f"\n⚠️ <b>ОШИБКА:</b> <code>{withdrawal.error_text}</code>")

    return "".join(message_parts)


@router.message(F.text.startswith("/withdrawals"))
async def list_withdrawals(message: Message):
    if message.from_user.id not in settings.admins:
        return

    page = 1
    async with SessionLocal() as session:
        withdrawals, total_count = await get_withdrawals_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    if not withdrawals:
        await message.answer("📭 <b>Нет заявок на вывод со статусом pending/processing</b>", parse_mode="HTML")
        return

    withdrawal = withdrawals[0]

    # Получаем последние ставки пользователя
    async with SessionLocal() as session:
        recent_bets = await get_user_recent_bets(session, withdrawal.user_gift.user_id)

    text = format_withdrawal_message(withdrawal, recent_bets, page, total_pages)
    kb = build_withdrawals_keyboard(page, total_pages, withdrawal.id)

    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=False)


@router.callback_query(F.data.startswith("withdraw_page:"))
async def paginate_withdrawals(cb: CallbackQuery):
    try:
        page = int(cb.data.split(":")[1])

        async with SessionLocal() as session:
            withdrawals, total_count = await get_withdrawals_page(session, page)

        total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

        # Проверяем, что запрашиваемая страница существует
        if page < 1 or page > total_pages or not withdrawals:
            await cb.answer("❌ Эта страница не существует!")
            return

        withdrawal = withdrawals[0]

        # Получаем последние ставки пользователя
        async with SessionLocal() as session:
            recent_bets = await get_user_recent_bets(session, withdrawal.user_gift.user_id)

        text = format_withdrawal_message(withdrawal, recent_bets, page, total_pages)
        kb = build_withdrawals_keyboard(page, total_pages, withdrawal.id)

        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=False)
        await cb.answer()

    except ValueError:
        await cb.answer("❌ Ошибка пагинации!")
    except Exception as e:
        await cb.answer("❌ Произошла ошибка!")


@router.callback_query(F.data == "current_withdraw_page")
async def handle_current_page(cb: CallbackQuery):
    """Обработчик нажатия на кнопку текущей страницы"""
    await cb.answer(f"📄 Вы на этой странице!")


@router.callback_query(F.data.startswith("confirm_withdraw:"))
async def confirm_withdrawal(cb: CallbackQuery):
    """Подтверждение заявки на вывод"""
    try:
        withdrawal_id = int(cb.data.split(":")[1])

        async with SessionLocal() as session:
            # Находим заявку
            stmt = (
                select(GiftWithdrawal)
                .where(GiftWithdrawal.id == withdrawal_id)
                .where(GiftWithdrawal.status.in_(["pending", "processing"]))
                .options(selectinload(GiftWithdrawal.user_gift))
            )
            result = await session.execute(stmt)
            withdrawal = result.scalar_one_or_none()

            if not withdrawal:
                await cb.answer("❌ Заявка не найдена или уже обработана!")
                return

            # Обновляем статус заявки на done
            withdrawal.status = "done"
            withdrawal.withdrawn_at = func.now()

            await session.commit()

            await cb.answer("✅ Заявка успешно подтверждена!")

            # Обновляем сообщение
            current_text = cb.message.text
            updated_text = current_text + f"\n\n✅ <b>ПОДТВЕРЖДЕНО АДМИНОМ</b>\n⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

            # Убираем кнопки действий
            keyboard = cb.message.reply_markup.inline_keyboard
            new_keyboard = [row for row in keyboard if not any(
                btn.callback_data.startswith(('confirm_withdraw:', 'reject_withdraw:')) for btn in row)]

            await cb.message.edit_text(
                updated_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard),
                parse_mode="HTML",
                disable_web_page_preview=False
            )

    except Exception as e:
        await cb.answer("❌ Ошибка при подтверждении заявки!")


@router.callback_query(F.data.startswith("reject_withdraw:"))
async def reject_withdrawal(cb: CallbackQuery):
    """Отклонение заявки на вывод"""
    try:
        withdrawal_id = int(cb.data.split(":")[1])

        async with SessionLocal() as session:
            # Находим заявку
            stmt = (
                select(GiftWithdrawal)
                .where(GiftWithdrawal.id == withdrawal_id)
                .where(GiftWithdrawal.status.in_(["pending", "processing"]))
                .options(selectinload(GiftWithdrawal.user_gift))
            )
            result = await session.execute(stmt)
            withdrawal = result.scalar_one_or_none()

            if not withdrawal:
                await cb.answer("❌ Заявка не найдена или уже обработана!")
                return

            # Обновляем статус заявки на failed (статус подарка не меняем)
            withdrawal.status = "failed"

            await session.commit()

            await cb.answer("❌ Заявка отклонена!")

            # Обновляем сообщение
            current_text = cb.message.text
            updated_text = current_text + f"\n\n❌ <b>ОТКЛОНЕНО АДМИНОМ</b>\n⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"

            # Убираем кнопки действий
            keyboard = cb.message.reply_markup.inline_keyboard
            new_keyboard = [row for row in keyboard if not any(
                btn.callback_data.startswith(('confirm_withdraw:', 'reject_withdraw:')) for btn in row)]

            await cb.message.edit_text(
                updated_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard),
                parse_mode="HTML",
                disable_web_page_preview=False
            )

    except Exception as e:
        await cb.answer("❌ Ошибка при отклонении заявки!")