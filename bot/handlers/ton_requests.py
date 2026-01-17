from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import html

from bot.config import settings
from bot.db import SessionLocal
from bot.models.users import User
from bot.models.bets import Bet
from bot.models.withdraw_request import WithdrawRequest

router = Router()

PAGE_SIZE = 1


# =========================
#   DB ACCESS
# =========================
async def get_failed_ton_withdrawals_page(session: AsyncSession, page: int):
    offset = (page - 1) * PAGE_SIZE
    stmt = (
        select(WithdrawRequest, User)
        .join(User, User.telegram_id == WithdrawRequest.user_id)
        .where(WithdrawRequest.status == "failed")
        .order_by(WithdrawRequest.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await session.execute(stmt)
    rows = result.all()

    withdrawals = [
        {"withdrawal": w, "user": u}
        for w, u in rows
    ]

    total_stmt = select(func.count(WithdrawRequest.id)).where(WithdrawRequest.status == "failed")
    total_result = await session.execute(total_stmt)
    total_count = total_result.scalar_one()

    return withdrawals, total_count


async def get_user_recent_bets(session: AsyncSession, user_id: int, limit: int = 5):
    stmt = (
        select(Bet)
        .where(Bet.user_id == user_id)
        .order_by(Bet.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# =========================
#   UI HELPERS
# =========================
def build_keyboard(current_page: int, total_pages: int, withdrawal_id: int) -> InlineKeyboardMarkup:
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"ton_page:{current_page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ton_current_page"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"ton_page:{current_page + 1}"))

    actions = [
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ton_confirm:{withdrawal_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"ton_reject:{withdrawal_id}")
    ]

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append(actions)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_bet_line(bet: Bet, index: int) -> str:
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


def format_withdrawal_message(withdrawal_data: dict, recent_bets: list, page: int, total_pages: int) -> str:
    withdrawal = withdrawal_data["withdrawal"]
    user = withdrawal_data["user"]

    created_at = withdrawal.created_at.strftime("%d.%m.%Y %H:%M") if withdrawal.created_at else "—"
    amount = f"{withdrawal.amount / 100:.2f} TON"
    username = f"@{html.escape(user.username)}" if user.username else "—"
    user_balance = f"{user.ton_balance / 100:.2f} TON" if user.ton_balance else "0.00 TON"

    message_parts = [
        f"💎 <b>ЗАЯВКА НА ВЫВОД TON</b>\n",
        f"📄 Страница: <b>{page}/{total_pages}</b>\n",
        f"⏰ Создана: <b>{created_at}</b>\n\n",

        f"💰 <b>ИНФОРМАЦИЯ О ВЫВОДЕ</b>\n",
        f"┣ Сумма: <b>{amount}</b>\n",
        f"┣ Адрес: <code>{withdrawal.address}</code>\n",
        f"┣ Попытки: {withdrawal.retries or 0}\n",
    ]

    if withdrawal.error_text:
        message_parts.append(f"┗ ⚠️ Ошибка: <code>{withdrawal.error_text}</code>\n")
    else:
        message_parts.append("┗ Ошибка: —\n")

    message_parts.extend([
        f"\n👤 <b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ</b>\n",
        f"┣ ID: <code>{user.telegram_id}</code>\n",
        f"┣ Имя: {html.escape(user.first_name) if user.first_name else '—'}\n",
        f"┣ Username: {username}\n",
        f"┗ Баланс: <b>{user_balance}</b>\n",
    ])

    if recent_bets:
        message_parts.append(f"\n🎰 <b>ПОСЛЕДНИЕ СТАВКИ ({len(recent_bets)})</b>\n")
        for i, bet in enumerate(recent_bets, 1):
            message_parts.append(format_bet_line(bet, i))
    else:
        message_parts.append(f"\n🎰 <b>ПОСЛЕДНИЕ СТАВКИ</b>\n┗ <i>Ставок не найдено</i>\n")

    return "".join(message_parts)


# =========================
#   HANDLERS
# =========================
@router.message(F.text.startswith("/ton_failed"))
async def list_ton_failed(message: Message):
    if message.from_user.id not in settings.admins:
        return

    page = 1
    async with SessionLocal() as session:
        withdrawals_data, total_count = await get_failed_ton_withdrawals_page(session, page)

    total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

    if not withdrawals_data:
        await message.answer("📭 <b>Нет TON-заявок со статусом failed</b>", parse_mode="HTML")
        return

    wd = withdrawals_data[0]
    async with SessionLocal() as session:
        recent_bets = await get_user_recent_bets(session, wd["user"].telegram_id)

    text = format_withdrawal_message(wd, recent_bets, page, total_pages)
    kb = build_keyboard(page, total_pages, wd["withdrawal"].id)
    await message.answer(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=False)


@router.callback_query(F.data.startswith("ton_page:"))
async def paginate_ton(cb: CallbackQuery):
    try:
        page = int(cb.data.split(":")[1])
        async with SessionLocal() as session:
            withdrawals_data, total_count = await get_failed_ton_withdrawals_page(session, page)
        total_pages = max((total_count + PAGE_SIZE - 1) // PAGE_SIZE, 1)

        if not withdrawals_data or page < 1 or page > total_pages:
            await cb.answer("❌ Нет такой страницы!")
            return

        wd = withdrawals_data[0]
        async with SessionLocal() as session:
            recent_bets = await get_user_recent_bets(session, wd["user"].telegram_id)

        text = format_withdrawal_message(wd, recent_bets, page, total_pages)
        kb = build_keyboard(page, total_pages, wd["withdrawal"].id)
        await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await cb.answer()
    except Exception:
        await cb.answer("⚠️ Ошибка пагинации!")


@router.callback_query(F.data == "ton_current_page")
async def ton_current_page(cb: CallbackQuery):
    await cb.answer("📄 Эта страница уже открыта.")


async def _update_status(cb: CallbackQuery, withdrawal_id: int, approved: bool):
    async with SessionLocal() as session:
        stmt = select(WithdrawRequest).where(WithdrawRequest.id == withdrawal_id, WithdrawRequest.status == "failed")
        result = await session.execute(stmt)
        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            await cb.answer("❌ Заявка не найдена или уже обработана!")
            return

        if approved:
            withdrawal.status = "pending"
            withdrawal.error_text = None
            withdrawal.retries = 0
        else:
            withdrawal.status = "done"

        await session.commit()

    mark = "✅ ПОДТВЕРЖДЕНО (переведено в pending)" if approved else "❌ ОТКЛОНЕНО"
    await cb.answer("✅ Готово!" if approved else "❌ Отклонено!")

    updated_text = cb.message.text + f"\n\n{mark} АДМИНОМ\n⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    kb = cb.message.reply_markup.inline_keyboard
    new_kb = [
        row for row in kb
        if not any(btn.callback_data.startswith(("ton_confirm:", "ton_reject:")) for btn in row)
    ]
    await cb.message.edit_text(
        updated_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=new_kb),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ton_confirm:"))
async def ton_confirm(cb: CallbackQuery):
    withdrawal_id = int(cb.data.split(":")[1])
    await _update_status(cb, withdrawal_id, approved=True)


@router.callback_query(F.data.startswith("ton_reject:"))
async def ton_reject(cb: CallbackQuery):
    withdrawal_id = int(cb.data.split(":")[1])
    await _update_status(cb, withdrawal_id, approved=False)
