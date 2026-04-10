from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, func
from db import SessionLocal
from models.users import User
from models.bets import Bet
from models.user_gift import UserGift
from models.withdraw_request import WithdrawRequest
from models.gift_withdrawals import GiftWithdrawal
from models.user_transaction import UserTransaction

from sqlalchemy.orm import selectinload


from config import settings

router = Router()


ITEMS_PER_PAGE = 10


GIFT_STATUS_MAP = {
    "AVAILABLE": "📦 В инвентаре",
    "LOCKED_IN_BET": "🎲 Поставлен",
    "SOLD": "💸 Продан",
    "WITHDRAWN": "🚀 Выведен",
    "PROCESSING": "⏳ В обработке",
}


# ==================================================
# Универсальные кнопки
# ==================================================
def build_pagination_keyboard(section: str, user_id: int, page: int, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    nav = []

    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅", callback_data=f"{section}:{user_id}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡", callback_data=f"{section}:{user_id}:{page + 1}"))

    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="↩ Назад", callback_data=f"user_info:{user_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Ставки", callback_data=f"user_bets:{user_id}:1"),
                InlineKeyboardButton(text="💎 Подарки", callback_data=f"user_gifts:{user_id}:1"),
            ],
            [
                InlineKeyboardButton(text="💰 Пополнения", callback_data=f"user_deposits:{user_id}:1"),
                InlineKeyboardButton(text="🏦 Выводы", callback_data=f"user_withdraws:{user_id}:1"),
            ],
        ]
    )


def build_back_button(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩ Назад", callback_data=f"user_info:{user_id}")]
        ]
    )


# ==================================================
# Получение и форматирование общей информации
# ==================================================
async def get_user_summary(session, user_id: int):
    user_stmt = select(User).where(User.telegram_id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    bets_result = await session.execute(
        select(
            func.count(Bet.id),
            func.coalesce(func.sum(Bet.amount_cents), 0),
            func.coalesce(func.sum(Bet.win_cents), 0),
        ).where(Bet.user_id == user_id)
    )
    bets_count, total_bet_cents, total_win_cents = bets_result.one()

    deposits_sum = await session.scalar(
        select(func.coalesce(func.sum(UserTransaction.amount), 0)).where(
            (UserTransaction.user_id == user_id) & (UserTransaction.type == "deposit")
        )
    )

    ton_withdraw_sum = await session.scalar(
        select(func.coalesce(func.sum(WithdrawRequest.amount), 0)).where(
            (WithdrawRequest.user_id == user_id) & (WithdrawRequest.status == "done")
        )
    )

    gift_withdraw_sum = await session.scalar(
        select(func.coalesce(func.sum(GiftWithdrawal.purchase_price_cents), 0)).where(
            (GiftWithdrawal.user_id == user_id) & (GiftWithdrawal.status == "done")
        )
    )

    return {
        "user": user,
        "bets_count": bets_count,
        "total_bet_cents": total_bet_cents,
        "total_win_cents": total_win_cents,
        "deposits_sum": deposits_sum,
        "ton_withdraw_sum": ton_withdraw_sum,
        "gift_withdraw_sum": gift_withdraw_sum,
    }


def format_user_summary(data: dict) -> str:
    user = data["user"]
    balance_ton = (user.ton_balance or 0) / 100
    username = f"@{user.username}" if user.username else "—"
    first_name = user.first_name or "Не указано"

    bet_sum_ton = data["total_bet_cents"] / 100
    win_sum_ton = data["total_win_cents"] / 100
    deposit_sum_ton = data["deposits_sum"] / 100
    withdraw_sum_ton = (data["ton_withdraw_sum"] + data["gift_withdraw_sum"]) / 100
    roi = (data["total_win_cents"] / data["total_bet_cents"]) * 100 if data["total_bet_cents"] else 0

    return (
        f"👤 <b>ПОЛЬЗОВАТЕЛЬ</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"👤 {username}\n"
        f"📛 {first_name}\n"
        f"💰 Баланс: <b>{balance_ton:.2f} TON</b>\n"
        f"👥 Реферер: <code>{user.referred_by or '—'}</code>\n"
        f"📅 Создан: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"\n"
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"🎲 Ставок: <b>{data['bets_count']}</b>\n"
        f"💸 Сумма ставок: <b>{bet_sum_ton:.2f} TON</b>\n"
        f"🏆 Выигрыши: <b>{win_sum_ton:.2f} TON</b>\n"
        f"📈 ROI: <b>{roi:.1f}%</b>\n"
        f"\n"
        f"💰 Пополнено: <b>{deposit_sum_ton:.2f} TON</b>\n"
        f"🏦 Выведено (всего): <b>{withdraw_sum_ton:.2f} TON</b>\n"
    )


# ==================================================
# Команда /user
# ==================================================
@router.message(Command("user"))
async def cmd_user(message: Message):
    if message.from_user.id not in settings.admins:
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("⚠️ Использование: <code>/user 123456789</code>", parse_mode="HTML")
        return

    user_id = int(parts[1])

    async with SessionLocal() as session:
        data = await get_user_summary(session, user_id)
    if not data:
        await message.answer("❌ Пользователь не найден.")
        return

    text = format_user_summary(data)
    await message.answer(text, parse_mode="HTML", reply_markup=build_user_actions_keyboard(user_id))


# ==================================================
# Возврат к профилю
# ==================================================
@router.callback_query(F.data.startswith("user_info:"))
async def cb_user_info(cb: CallbackQuery):
    user_id = int(cb.data.split(":")[1])
    async with SessionLocal() as session:
        data = await get_user_summary(session, user_id)
    if not data:
        await cb.answer("❌ Пользователь не найден.")
        return
    await cb.message.edit_text(format_user_summary(data), parse_mode="HTML", reply_markup=build_user_actions_keyboard(user_id))
    await cb.answer()


# ==================================================
# Универсальный шаблон для разделов с пагинацией
# ==================================================
async def paginate_query(model, user_id: int, page: int, order_field, filter_field, filter_value, extra_filters=None, options=None):
    offset = (page - 1) * ITEMS_PER_PAGE
    stmt = select(model).where(getattr(model, filter_field) == filter_value)
    if extra_filters:
        for f in extra_filters:
            stmt = stmt.where(f)
    if options:
        stmt = stmt.options(*options)
    stmt = stmt.order_by(order_field.desc()).offset(offset).limit(ITEMS_PER_PAGE + 1)
    async with SessionLocal() as session:
        result = await session.execute(stmt)
        items = result.scalars().all()
    has_next = len(items) > ITEMS_PER_PAGE
    return items[:ITEMS_PER_PAGE], has_next


# ==================================================
# Ставки
# ==================================================
@router.callback_query(F.data.startswith("user_bets:"))
async def cb_user_bets(cb: CallbackQuery):
    _, user_id, page = cb.data.split(":")
    user_id, page = int(user_id), int(page)
    bets, has_next = await paginate_query(Bet, user_id, page, Bet.created_at, "user_id", user_id)

    if not bets:
        await cb.message.edit_text("🎲 Нет ставок.", reply_markup=build_back_button(user_id))
        return

    lines = []
    for b in bets:
        asset = "💰 TON" if b.asset_type == "FIAT" else "🎁 Подарок"
        final_gift = f"\n┗ 🎁 {b.final_gift_title}" if getattr(b, "final_gift_title", None) else ""
        lines.append(
            f"🎰 <b>#{b.id}</b> ({asset})\n"
            f"┣ 💸 {b.amount_cents / 100:.2f} TON\n"
            f"┣ 🏆 {b.win_cents / 100:.2f} TON\n"
            f"┣ ⏰ {b.created_at.strftime('%Y-%m-%d %H:%M')}{final_gift}\n"
        )

    await cb.message.edit_text(
        "<b>🎲 СТАВКИ</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_pagination_keyboard("user_bets", user_id, page, has_next),
    )



# ==================================================
# Депозиты
# ==================================================
@router.callback_query(F.data.startswith("user_deposits:"))
async def cb_user_deposits(cb: CallbackQuery):
    _, user_id, page = cb.data.split(":")
    user_id, page = int(user_id), int(page)
    deposits, has_next = await paginate_query(
        UserTransaction,
        user_id,
        page,
        UserTransaction.created_at,
        "user_id",
        user_id,
        extra_filters=[UserTransaction.type == "deposit"],
    )

    if not deposits:
        await cb.message.edit_text("💰 Нет депозитов.", reply_markup=build_back_button(user_id))
        return

    lines = []
    for d in deposits:
        currency = "💰 TON" if d.currency == "ton" else "🎁 Подарок"
        date = d.created_at.strftime('%Y-%m-%d %H:%M')
        lines.append(
            f"{currency}\n"
            f"┣ 💸 {d.amount / 100:.2f} TON\n"
            f"┗ ⏰ {date}\n"
        )

    await cb.message.edit_text(
        "<b>💰 ПОПОЛНЕНИЯ</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_pagination_keyboard("user_deposits", user_id, page, has_next),
    )




# ==================================================
# Подарки
# ==================================================
@router.callback_query(F.data.startswith("user_gifts:"))
async def cb_user_gifts(cb: CallbackQuery):
    _, user_id, page = cb.data.split(":")
    user_id, page = int(user_id), int(page)
    gifts, has_next = await paginate_query(
        UserGift,
        user_id,
        page,
        UserGift.received_at,
        "user_id",
        user_id,
        options=[selectinload(UserGift.gift_catalog)]
    )
    if not gifts:
        await cb.message.edit_text("💎 Нет подарков.", reply_markup=build_back_button(user_id))
        return

    lines = []
    for g in gifts:
        status = GIFT_STATUS_MAP.get(g.status, g.status)
        title = g.gift_catalog.title if g.gift_catalog else f"Gift #{g.id}"
        price = (g.price_cents or 0) / 100
        date = g.received_at.strftime('%Y-%m-%d %H:%M') if g.received_at else "—"
        lines.append(
            f"🎁 <b>{title}</b>\n"
            f"┣ 💰 {price:.2f} TON\n"
            f"┣ 📦 {status}\n"
            f"┗ ⏰ {date}\n"
        )

    await cb.message.edit_text(
        "<b>💎 ПОДАРКИ</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_pagination_keyboard("user_gifts", user_id, page, has_next),
    )



# ==================================================
# Выводы
# ==================================================
@router.callback_query(F.data.startswith("user_withdraws:"))
async def cb_user_withdraws(cb: CallbackQuery):
    _, user_id, page = cb.data.split(":")
    user_id, page = int(user_id), int(page)
    ton_withdraws, has_next1 = await paginate_query(
        WithdrawRequest,
        user_id,
        page,
        WithdrawRequest.created_at,
        "user_id",
        user_id,
        extra_filters=[WithdrawRequest.status == "done"],
    )
    gift_withdraws, has_next2 = await paginate_query(
        GiftWithdrawal,
        user_id,
        page,
        GiftWithdrawal.created_at,
        "user_id",
        user_id,
        extra_filters=[GiftWithdrawal.status == "done"],
    )

    has_next = has_next1 or has_next2
    lines = []

    for w in ton_withdraws:
        lines.append(
            f"🏦 TON вывод\n"
            f"┣ 💸 {w.amount / 100:.2f} TON\n"
            f"┗ ⏰ {w.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )

    for g in gift_withdraws:
        price = (g.purchase_price_cents or 0) / 100
        lines.append(
            f"🎁 Gift вывод\n"
            f"┣ 💰 {price:.2f} TON\n"
            f"┗ ⏰ {g.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )

    if not lines:
        await cb.message.edit_text("🏦 Нет завершённых выводов.", reply_markup=build_back_button(user_id))
        return

    await cb.message.edit_text(
        "<b>🏦 ВЫВОДЫ</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_pagination_keyboard("user_withdraws", user_id, page, has_next),
    )

