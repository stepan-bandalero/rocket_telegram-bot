from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.db import SessionLocal
from bot.middlewares.db import DataBaseSessionMiddleware
from bot.models.bets import Bet
from bot.models.gift_withdrawals import GiftWithdrawal
from bot.models.promo import PromoLink, PromoReferral
from bot.models.referral_earnings import ReferralEarning
from bot.models.user_gift import UserGift
from bot.models.user_transaction import UserTransaction
from bot.models.users import User
from bot.models.withdraw_request import WithdrawRequest
from bot.services.promo import PromoService
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = Router()
router.message.middleware(DataBaseSessionMiddleware())

ITEMS_PER_PAGE = 1  # Одна промо-ссылка на страницу


# ==================================================
# Универсальные кнопки для промо-системы
# ==================================================
def build_promo_pagination_keyboard(section: str, promo_id: int, page: int, has_prev: bool, has_next: bool,
                                    extra_buttons=None) -> InlineKeyboardMarkup:
    buttons = []
    nav = []

    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"{section}:{promo_id}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперед ➡", callback_data=f"{section}:{promo_id}:{page + 1}"))

    if nav:
        buttons.append(nav)

    if extra_buttons:
        buttons.extend(extra_buttons)

    buttons.append([InlineKeyboardButton(text="↩ Назад к промо", callback_data=f"promo_info:{promo_id}")])
    buttons.append([InlineKeyboardButton(text="🏠 Все промо-ссылки", callback_data="promos_list:1")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_promo_actions_keyboard(promo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Пользователи", callback_data=f"promo_users:{promo_id}:1"),
                InlineKeyboardButton(text="💰 Реферальные отчисления",
                                     callback_data=f"promo_referral_earnings:{promo_id}:1"),
            ],
            [
                InlineKeyboardButton(text="🏠 Все промо-ссылки", callback_data="promos_list:1"),
            ]
        ]
    )


def build_promos_list_keyboard(page: int, has_prev: bool, has_next: bool, promo_id: int = None) -> InlineKeyboardMarkup:
    buttons = []
    nav = []

    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"promos_list:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперед ➡", callback_data=f"promos_list:{page + 1}"))

    if nav:
        buttons.append(nav)

    # Добавляем кнопку для детального просмотра, если указан promo_id
    if promo_id:
        buttons.append([InlineKeyboardButton(text="📊 Детальная статистика", callback_data=f"promo_info:{promo_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================================================
# Получение и форматирование статистики по промо-ссылке
# ==================================================
async def get_promo_stats(session: AsyncSession, promo_id: int):
    """Получение полной статистики по промо-ссылке"""
    # Основная информация о промо с загрузкой рефералов
    promo_stmt = (
        select(PromoLink)
        .where(PromoLink.id == promo_id)
        .options(selectinload(PromoLink.referrals))
    )
    promo_result = await session.execute(promo_stmt)
    promo = promo_result.scalar_one_or_none()

    if not promo:
        return None

    # Получаем ID всех рефералов этой промо-ссылки
    referral_user_ids = [ref.user_id for ref in promo.referrals]

    # Реальные реферальные отчисления
    actual_earnings = await session.scalar(
        select(func.coalesce(func.sum(ReferralEarning.amount), 0)).where(
            ReferralEarning.referrer_id == promo.created_by
        )
    )

    # Инициализируем статистику с нулевыми значениями
    stats = {
        "promo": promo,
        "referral_count": len(referral_user_ids),
        "actual_earnings": actual_earnings or 0,
        "deposits_ton": 0,
        "deposits_gift": 0,
        "gift_deposits_count": 0,
        "ton_withdrawals": 0,
        "gift_withdrawals": 0,
        "active_users": 0,
    }

    if not referral_user_ids:
        return stats

    # Сумма депозитов в TON
    deposits_ton = await session.scalar(
        select(func.coalesce(func.sum(UserTransaction.amount), 0)).where(
            (UserTransaction.user_id.in_(referral_user_ids)) &
            (UserTransaction.type == "deposit") &
            (UserTransaction.currency == "ton")
        )
    )

    # Сумма депозитов в подарках
    deposits_gift = await session.scalar(
        select(func.coalesce(func.sum(UserTransaction.amount), 0)).where(
            (UserTransaction.user_id.in_(referral_user_ids)) &
            (UserTransaction.type == "deposit") &
            (UserTransaction.currency == "gift")
        )
    )

    # Количество пополнений подарков
    gift_deposits_count = await session.scalar(
        select(func.count(UserTransaction.id)).where(
            (UserTransaction.user_id.in_(referral_user_ids)) &
            (UserTransaction.type == "deposit") &
            (UserTransaction.currency == "gift")
        )
    )

    # Сумма выводов TON
    ton_withdrawals = await session.scalar(
        select(func.coalesce(func.sum(WithdrawRequest.amount), 0)).where(
            (WithdrawRequest.user_id.in_(referral_user_ids)) &
            (WithdrawRequest.status == "done")
        )
    )

    # Сумма выводов подарков
    gift_withdrawals = await session.scalar(
        select(func.coalesce(func.sum(GiftWithdrawal.purchase_price_cents), 0)).where(
            (GiftWithdrawal.user_id.in_(referral_user_ids)) &
            (GiftWithdrawal.status == "done")
        )
    )

    # Активные пользователи (те, у кого есть депозиты)
    active_users = await session.scalar(
        select(func.count(func.distinct(UserTransaction.user_id))).where(
            (UserTransaction.user_id.in_(referral_user_ids)) &
            (UserTransaction.type == "deposit")
        )
    )

    stats.update({
        "deposits_ton": deposits_ton or 0,
        "deposits_gift": deposits_gift or 0,
        "gift_deposits_count": gift_deposits_count or 0,
        "ton_withdrawals": ton_withdrawals or 0,
        "gift_withdrawals": gift_withdrawals or 0,
        "active_users": active_users or 0,
    })

    return stats


def format_promo_stats(stats: dict) -> str:
    """Форматирование статистики промо-ссылки"""
    promo = stats["promo"]
    promo_url = f"{settings.bot_href}?start={promo.code}"

    # Преобразуем все к float для совместимости
    deposits_ton_ton = float(stats["deposits_ton"] / 100)
    deposits_gift_ton = float(stats["deposits_gift"] / 100)
    total_deposits_ton = deposits_ton_ton + deposits_gift_ton
    ton_withdrawals_ton = float(stats["ton_withdrawals"] / 100)
    gift_withdrawals_ton = float(stats["gift_withdrawals"] / 100)
    total_withdrawals_ton = ton_withdrawals_ton + gift_withdrawals_ton
    actual_earnings_ton = float(stats["actual_earnings"] / 100)

    # Расчетные отчисления (на основе процента от депозитов)
    calculated_earnings = total_deposits_ton * (promo.referral_percentage / 100)

    return (
        f"🎫 <b>ПРОМО-ССЫЛКА</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
        f"👤 <b>Создал:</b> <code>{promo.created_by}</code>\n"
        f"📈 <b>Процент:</b> <b>{promo.referral_percentage}%</b>\n"
        f"📅 <b>Создана:</b> {promo.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"\n"
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"👥 <b>Переходов:</b> {stats['referral_count']}\n"
        f"🟢 <b>Активных:</b> {stats['active_users']}\n"
        f"\n"
        f"💰 <b>Пополнения:</b>\n"
        f"  ┣ TON: <b>{deposits_ton_ton:,.2f} TON</b>\n"
        f"  ┣ Подарки: <b>{deposits_gift_ton:,.2f} TON</b>\n"
        f"  ┗ Всего: <b>{total_deposits_ton:,.2f} TON</b>\n"
        f"\n"
        f"🎁 <b>Пополнения подарков:</b>\n"
        f"  ┣ Количество: <b>{stats['gift_deposits_count']}</b>\n"
        f"  ┗ Сумма: <b>{deposits_gift_ton:,.2f} TON</b>\n"
        f"\n"
        f"🏦 <b>Выводы:</b>\n"
        f"  ┣ TON: <b>{ton_withdrawals_ton:,.2f} TON</b>\n"
        f"  ┣ Подарки: <b>{gift_withdrawals_ton:,.2f} TON</b>\n"
        f"  ┗ Всего: <b>{total_withdrawals_ton:,.2f} TON</b>\n"
        f"\n"
        f"💸 <b>РЕФЕРАЛЬНЫЕ ОТЧИСЛЕНИЯ</b>\n"
        f"  ┣ Фактические: <b>{actual_earnings_ton:,.2f} TON</b>\n"
        f"  ┗ Расчетные: <b>{calculated_earnings:,.2f} TON</b>\n"
    )


def format_promo_basic_info(promo: PromoLink, referrals_count: int, total_deposits_ton: float, page: int,
                            total_pages: int) -> str:
    """Форматирование базовой информации о промо-ссылке"""
    promo_url = f"{settings.bot_href}?start={promo.code}"

    return (
        f"🎫 <b>ПРОМО-ССЫЛКА #{promo.id}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
        f"👤 <b>Создал:</b> <code>{promo.created_by}</code>\n"
        f"📈 <b>Процент:</b> <b>{promo.referral_percentage}%</b>\n"
        f"👥 <b>Переходов:</b> <b>{referrals_count}</b>\n"
        f"💰 <b>Сумма пополнений:</b> <b>{total_deposits_ton:,.2f} TON</b>\n"
        f"📅 <b>Создана:</b> {promo.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"\n"
        f"📄 Страница: <b>{page}</b> из <b>{total_pages}</b>"
    )


# ==================================================
# Команда /promos с пагинацией (по одной ссылке на страницу)
# ==================================================
@router.message(Command("promos"))
async def cmd_promos(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    await show_promos_list(message, session, 1)


async def show_promos_list(target, session: AsyncSession, page: int):
    """Показать список промо-ссылок с пагинацией (одна ссылка на страницу)"""
    # Получаем общее количество промо-ссылок
    total_promos = await session.scalar(select(func.count(PromoLink.id)))
    total_pages = total_promos  # По одной ссылке на страницу

    if total_promos == 0:
        if hasattr(target, 'message'):
            await target.message.edit_text("📭 Промо-ссылок пока нет.")
        else:
            await target.answer("📭 Промо-ссылок пока нет.")
        return

    # Ограничиваем номер страницы в допустимых пределах
    page = max(1, min(page, total_pages))

    # Получаем промо-ссылку для текущей страницы (сортировка от новых к старым)
    promo_stmt = (
        select(PromoLink)
        .order_by(PromoLink.id.desc())  # Сортируем по ID в порядке убывания (новые сначала)
        .offset(page - 1)  # Смещение равно номеру страницы минус 1
        .limit(1)
    )
    promo_result = await session.execute(promo_stmt)
    promo = promo_result.scalar_one_or_none()

    if not promo:
        if hasattr(target, 'message'):
            await target.message.edit_text("❌ Промо-ссылка не найдена.")
        else:
            await target.answer("❌ Промо-ссылка не найдена.")
        return

    # Базовая статистика для промо-ссылки
    referrals_count = await session.scalar(
        select(func.count(PromoReferral.id)).where(PromoReferral.promo_id == promo.id)
    )

    total_deposits = await session.scalar(
        select(func.coalesce(func.sum(UserTransaction.amount), 0))
        .join(PromoReferral, UserTransaction.user_id == PromoReferral.user_id)
        .where(
            (PromoReferral.promo_id == promo.id) &
            (UserTransaction.type == "deposit")
        )
    )
    total_deposits_ton = total_deposits / 100 if total_deposits else 0

    text = format_promo_basic_info(promo, referrals_count, total_deposits_ton, page, total_pages)

    # Определяем наличие предыдущей и следующей страницы
    has_prev = page > 1
    has_next = page < total_pages

    # Создаем клавиатуру с пагинацией и кнопкой для детальной информации
    keyboard = build_promos_list_keyboard(page, has_prev, has_next, promo.id)

    # Редактируем существующее сообщение вместо отправки нового
    if hasattr(target, 'message'):  # Если это CallbackQuery
        await target.message.edit_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    else:  # Если это Message
        await target.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )


# ==================================================
# Просмотр детальной информации о промо-ссылке
# ==================================================
@router.callback_query(F.data.startswith("promo_info:"))
async def cb_promo_info(cb: CallbackQuery):
    promo_id = int(cb.data.split(":")[1])

    async with SessionLocal() as session:
        stats = await get_promo_stats(session, promo_id)

    if not stats:
        await cb.answer("❌ Промо-ссылка не найдена.")
        return

    text = format_promo_stats(stats)
    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=build_promo_actions_keyboard(promo_id)
    )
    await cb.answer()


# ==================================================
# Список промо-ссылок (пагинация) - теперь редактирует существующее сообщение
# ==================================================
@router.callback_query(F.data.startswith("promos_list:"))
async def cb_promos_list(cb: CallbackQuery):
    page = int(cb.data.split(":")[1])

    async with SessionLocal() as session:
        await show_promos_list(cb, session, page)

    await cb.answer()


# ==================================================
# Пользователи промо-ссылки
# ==================================================
@router.callback_query(F.data.startswith("promo_users:"))
async def cb_promo_users(cb: CallbackQuery):
    parts = cb.data.split(":")

    # Обрабатываем оба случая: с promo_id и без (пагинация)
    if len(parts) == 3:
        # Первый вызов: promo_users:promo_id:page
        _, promo_id, page = parts
        promo_id, page = int(promo_id), int(page)
    elif len(parts) == 2:
        # Пагинация: promo_users:page (используем promo_id из текущего состояния)
        # Нужно получить promo_id из текущего сообщения или сохранить в состоянии
        # Временно используем заглушку - нужно будет доработать
        await cb.answer("❌ Ошибка пагинации. Вернитесь к промо-ссылке.")
        return
    else:
        await cb.answer("❌ Неверный формат данных.")
        return

    offset = (page - 1) * ITEMS_PER_PAGE

    async with SessionLocal() as session:
        # Получаем пользователей с пагинацией через связь PromoReferral
        users_stmt = (
            select(User)
            .join(PromoReferral, User.telegram_id == PromoReferral.user_id)
            .where(PromoReferral.promo_id == promo_id)
            .order_by(PromoReferral.created_at.desc())
            .offset(offset)
            .limit(ITEMS_PER_PAGE + 1)
        )
        users_result = await session.execute(users_stmt)
        users = users_result.scalars().all()

        has_next = len(users) > ITEMS_PER_PAGE
        users = users[:ITEMS_PER_PAGE]

        if not users:
            await cb.message.edit_text(
                "👥 Нет пользователей по этой промо-ссылке.",
                reply_markup=build_promo_pagination_keyboard("promo_users", promo_id, page, page > 1, has_next)
            )
            return

        text = f"👥 <b>ПОЛЬЗОВАТЕЛИ ПО ПРОМО-ССЫЛКЕ #{promo_id}</b>\n\n"

        for user in users:
            # Получаем дату регистрации по промо-ссылке
            promo_ref_stmt = select(PromoReferral).where(
                (PromoReferral.promo_id == promo_id) &
                (PromoReferral.user_id == user.telegram_id)
            )
            promo_ref_result = await session.execute(promo_ref_stmt)
            promo_ref = promo_ref_result.scalar_one_or_none()

            ref_date = promo_ref.created_at.strftime('%d.%m.%Y %H:%M') if promo_ref else "—"

            # Статистика по каждому пользователю
            deposits_ton = await session.scalar(
                select(func.coalesce(func.sum(UserTransaction.amount), 0)).where(
                    (UserTransaction.user_id == user.telegram_id) &
                    (UserTransaction.type == "deposit") &
                    (UserTransaction.currency == "ton")
                )
            )

            deposits_gift = await session.scalar(
                select(func.coalesce(func.sum(UserTransaction.amount), 0)).where(
                    (UserTransaction.user_id == user.telegram_id) &
                    (UserTransaction.type == "deposit") &
                    (UserTransaction.currency == "gift")
                )
            )

            gift_deposits_count = await session.scalar(
                select(func.count(UserTransaction.id)).where(
                    (UserTransaction.user_id == user.telegram_id) &
                    (UserTransaction.type == "deposit") &
                    (UserTransaction.currency == "gift")
                )
            )

            ton_withdrawals = await session.scalar(
                select(func.coalesce(func.sum(WithdrawRequest.amount), 0)).where(
                    (WithdrawRequest.user_id == user.telegram_id) &
                    (WithdrawRequest.status == "done")
                )
            )

            gift_withdrawals = await session.scalar(
                select(func.coalesce(func.sum(GiftWithdrawal.purchase_price_cents), 0)).where(
                    (GiftWithdrawal.user_id == user.telegram_id) &
                    (GiftWithdrawal.status == "done")
                )
            )

            username = f"@{user.username}" if user.username else "—"
            balance_ton = (user.ton_balance or 0) / 100
            deposits_ton_ton = float(deposits_ton or 0) / 100
            deposits_gift_ton = float(deposits_gift or 0) / 100
            ton_withdrawals_ton = float(ton_withdrawals or 0) / 100
            gift_withdrawals_ton = float(gift_withdrawals or 0) / 100

            text += (
                f"👤 <b>{username}</b> (<code>{user.telegram_id}</code>)\n"
                f"┣ 📅 Зарегистрирован: {ref_date}\n"
                f"┣ 💰 Баланс: <b>{balance_ton:.2f} TON</b>\n"
                f"┣ 💎 Пополнения TON: <b>{deposits_ton_ton:.2f} TON</b>\n"
                f"┣ 🎁 Пополнения подарков: <b>{deposits_gift_ton:.2f} TON</b>\n"
                f"┣ 📦 Кол-во подарков: <b>{gift_deposits_count}</b>\n"
                f"┣ 🏦 Выводы TON: <b>{ton_withdrawals_ton:.2f} TON</b>\n"
                f"┗ 🚀 Выводы подарков: <b>{gift_withdrawals_ton:.2f} TON</b>\n\n"
            )

        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=build_promo_pagination_keyboard("promo_users", promo_id, page, page > 1, has_next)
        )

    await cb.answer()


# ==================================================
# Реферальные отчисления
# ==================================================
@router.callback_query(F.data.startswith("promo_referral_earnings:"))
async def cb_promo_referral_earnings(cb: CallbackQuery):
    parts = cb.data.split(":")

    # Обрабатываем оба случая: с promo_id и без (пагинация)
    if len(parts) == 3:
        # Первый вызов: promo_referral_earnings:promo_id:page
        _, promo_id, page = parts
        promo_id, page = int(promo_id), int(page)
    elif len(parts) == 2:
        # Пагинация: promo_referral_earnings:page (используем promo_id из текущего состояния)
        # Нужно получить promo_id из текущего сообщения или сохранить в состоянии
        # Временно используем заглушку - нужно будет доработать
        await cb.answer("❌ Ошибка пагинации. Вернитесь к промо-ссылке.")
        return
    else:
        await cb.answer("❌ Неверный формат данных.")
        return

    offset = (page - 1) * ITEMS_PER_PAGE

    async with SessionLocal() as session:
        # Получаем информацию о промо-ссылке
        promo_stmt = select(PromoLink).where(PromoLink.id == promo_id)
        promo_result = await session.execute(promo_stmt)
        promo = promo_result.scalar_one_or_none()

        if not promo:
            await cb.answer("❌ Промо-ссылка не найдена.")
            return

        # Получаем реферальные отчисления с пагинацией
        earnings_stmt = (
            select(ReferralEarning)
            .where(ReferralEarning.referrer_id == promo.created_by)
            .order_by(ReferralEarning.created_at.desc())
            .offset(offset)
            .limit(ITEMS_PER_PAGE + 1)
            .options(selectinload(ReferralEarning.referred_user_id))  # Исправлено: referred_user вместо referred_user_id
        )
        earnings_result = await session.execute(earnings_stmt)
        earnings = earnings_result.scalars().all()

        has_next = len(earnings) > ITEMS_PER_PAGE
        earnings = earnings[:ITEMS_PER_PAGE]

        # Общая статистика по отчислениям
        total_earnings = await session.scalar(
            select(func.coalesce(func.sum(ReferralEarning.amount), 0)).where(
                ReferralEarning.referrer_id == promo.created_by
            )
        )

        # Статистика по типам отчислений
        gift_earnings = await session.scalar(
            select(func.coalesce(func.sum(ReferralEarning.amount), 0)).where(
                (ReferralEarning.referrer_id == promo.created_by) &
                (ReferralEarning.source_type == "gift_deposit")
            )
        )

        ton_earnings = await session.scalar(
            select(func.coalesce(func.sum(ReferralEarning.amount), 0)).where(
                (ReferralEarning.referrer_id == promo.created_by) &
                (ReferralEarning.source_type == "ton_deposit")
            )
        )

        # Количество уникальных рефералов, принесших доход
        unique_referrals = await session.scalar(
            select(func.count(func.distinct(ReferralEarning.referred_user_id))).where(
                ReferralEarning.referrer_id == promo.created_by
            )
        )

        total_earnings_ton = float(total_earnings or 0) / 100
        gift_earnings_ton = float(gift_earnings or 0) / 100
        ton_earnings_ton = float(ton_earnings or 0) / 100

        if not earnings:
            text = (
                f"💰 <b>РЕФЕРАЛЬНЫЕ ОТЧИСЛЕНИЯ</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>Получатель:</b> <code>{promo.created_by}</code>\n"
                f"🔗 <b>Промо-ссылка:</b> <code>{promo.code}</code>\n"
                f"📈 <b>Процент:</b> <b>{promo.referral_percentage}%</b>\n"
                f"\n"
                f"📊 <b>СТАТИСТИКА</b>\n"
                f"💸 Всего заработано: <b>{total_earnings_ton:,.2f} TON</b>\n"
                f"🎁 От подарков: <b>{gift_earnings_ton:,.2f} TON</b>\n"
                f"💰 От TON: <b>{ton_earnings_ton:,.2f} TON</b>\n"
                f"👥 Приносящих доход: <b>{unique_referrals}</b>\n"
                f"\n"
                f"📭 <b>Нет записей об отчислениях</b>\n"
            )
        else:
            text = (
                f"💰 <b>РЕФЕРАЛЬНЫЕ ОТЧИСЛЕНИЯ</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>Получатель:</b> <code>{promo.created_by}</code>\n"
                f"🔗 <b>Промо-ссылка:</b> <code>{promo.code}</code>\n"
                f"📈 <b>Процент:</b> <b>{promo.referral_percentage}%</b>\n"
                f"\n"
                f"📊 <b>ОБЩАЯ СТАТИСТИКА</b>\n"
                f"💸 Всего заработано: <b>{total_earnings_ton:,.2f} TON</b>\n"
                f"🎁 От подарков: <b>{gift_earnings_ton:,.2f} TON</b>\n"
                f"💰 От TON: <b>{ton_earnings_ton:,.2f} TON</b>\n"
                f"👥 Приносящих доход: <b>{unique_referrals}</b>\n"
                f"\n"
                f"📋 <b>ПОСЛЕДНИЕ ОТЧИСЛЕНИЯ</b>\n\n"
            )

            for earning in earnings:
                amount_ton = float(earning.amount) / 100
                source_emoji = "🎁" if earning.source_type == "gift_deposit" else "💰"
                source_text = "подарок" if earning.source_type == "gift_deposit" else "TON"

                referred_username = f"@{earning.referred_user.username}" if earning.referred_user and earning.referred_user.username else f"ID: {earning.referred_user_id}"

                text += (
                    f"{source_emoji} <b>{amount_ton:.2f} TON</b> от {referred_username}\n"
                    f"┣ 📊 Тип: {source_text}\n"
                    f"┗ ⏰ {earning.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                )

        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=build_promo_pagination_keyboard("promo_referral_earnings", promo_id, page, page > 1, has_next)
        )

    await cb.answer()


# ==================================================
# Существующие команды (оставляем как есть)
# ==================================================
@router.message(F.text.startswith("/add_promo"))
async def add_promo(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return

    try:
        _, tg_id_str, percent_str = message.text.split(maxsplit=2)
        tg_id = int(tg_id_str.strip())
        percent = int(percent_str.strip())

        if not (0 < percent <= 100):
            raise ValueError("invalid percent")

    except (ValueError, IndexError):
        await message.answer("❌ Используй: <code>/add_promo &lt;telegram_id&gt; &lt;процент&gt;</code>")
        return

    promo = await PromoService.create_promo(session, tg_id, percent)

    promo_url = f"{settings.bot_href}?start={promo.code}"

    text = (
        "🎉 <b>Реферальная ссылка создана!</b>\n\n"
        f"🔗 <b>Ссылка:</b> <code>{promo_url}</code>\n"
        f"👤 <b>Админ:</b> <code>{promo.created_by}</code>\n"
        f"📈 <b>Процент:</b> <code>{promo.referral_percentage}%</code>"
    )

    await message.answer(text, disable_web_page_preview=True)


@router.message(F.text.startswith("/delete_promo"))
async def delete_promo(message: Message, session: AsyncSession):
    if message.from_user.id not in settings.admins:
        return
    try:
        _, promo_code = message.text.split(maxsplit=1)
        promo_code = promo_code.strip()
    except ValueError:
        await message.answer("❌ Используй: <code>/delete_promo &lt;код&gt;</code>", parse_mode="HTML")
        return

    deleted = await PromoService.delete_promo(session, promo_code)
    if deleted:
        await message.answer(
            f"🗑 Промо с кодом <code>{promo_code}</code> удален.", parse_mode="HTML"
        )
    else:
        await message.answer("⚠ Промо не найден.", parse_mode="HTML")