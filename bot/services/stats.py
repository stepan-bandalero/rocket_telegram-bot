#
# from sqlalchemy import desc, func, cast, BigInteger, case, and_, select
# import pytz
# from datetime import datetime, timedelta, time
# from aiogram import Bot
# from aiogram.types import Message
# import aiohttp
#
# from bot.models.bets import Bet
# from bot.models.user_transaction import UserTransaction
# from bot.models.users import User
# from bot.models.star_invoice import StarsInvoice
# from bot.models.user_spins import UserSpin
# from bot.models.user_gift_upgrades import UserGiftUpgrade
# from bot.models.plinko_games import PlinkoGame
#
# def get_today_start_moscow_utc():
#     """Возвращает начало сегодняшнего дня по МСК в UTC"""
#     moscow_tz = pytz.timezone('Europe/Moscow')
#     now_moscow = datetime.now(moscow_tz)
#     today_moscow = now_moscow.replace(hour=0, minute=0, second=0, microsecond=0)
#     return today_moscow.astimezone(pytz.UTC).replace(tzinfo=None)
#
#
# # 🔹 Статистика по режимам за все время
# async def get_games_statistics_all_time(session):
#     # Кейсы (user_spins)
#     spins_total = await session.execute(
#         select(func.count(UserSpin.id))
#     )
#     spins_count = spins_total.scalar() or 0
#
#     # Апгрейды подарков (user_gift_upgrades)
#     upgrades_total = await session.execute(
#         select(func.count(UserGiftUpgrade.id))
#     )
#     upgrades_count = upgrades_total.scalar() or 0
#
#     # Plinko игры
#     plinko_total = await session.execute(
#         select(func.count(PlinkoGame.id))
#     )
#     plinko_count = plinko_total.scalar() or 0
#
#     # Звезды всего пополнено
#     stars_total = await session.execute(
#         select(func.sum(StarsInvoice.amount))
#         .where(StarsInvoice.status == 'paid')
#     )
#     total_stars = stars_total.scalar() or 0
#
#     return {
#         "spins_total": spins_count,
#         "upgrades_total": upgrades_count,
#         "plinko_total": plinko_count,
#         "total_games": spins_count + upgrades_count + plinko_count,
#         "total_stars": total_stars
#     }
#
#
# # 🔹 Статистика по режимам за последние 24ч
# async def get_games_statistics_24h(session):
#     # Начало сегодняшнего дня по МСК (00:00)
#     today_start_utc = get_today_start_moscow_utc()
#
#     # Кейсы за 24ч
#     spins_24h = await session.execute(
#         select(func.count(UserSpin.id))
#         .where(UserSpin.created_at >= today_start_utc)
#     )
#     spins_count_24h = spins_24h.scalar() or 0
#
#     # Апгрейды подарков за 24ч
#     upgrades_24h = await session.execute(
#         select(func.count(UserGiftUpgrade.id))
#         .where(UserGiftUpgrade.created_at >= today_start_utc)
#     )
#     upgrades_count_24h = upgrades_24h.scalar() or 0
#
#     # Plinko игры за 24ч
#     plinko_24h = await session.execute(
#         select(func.count(PlinkoGame.id))
#         .where(PlinkoGame.created_at >= today_start_utc)
#     )
#     plinko_count_24h = plinko_24h.scalar() or 0
#
#     # Звезды пополнено за 24ч
#     stars_24h = await session.execute(
#         select(func.sum(StarsInvoice.amount))
#         .where(and_(
#             StarsInvoice.status == 'paid',
#             StarsInvoice.created_at >= today_start_utc
#         ))
#     )
#     stars_24h_sum = stars_24h.scalar() or 0
#
#     return {
#         "spins_24h": spins_count_24h,
#         "upgrades_24h": upgrades_count_24h,
#         "plinko_24h": plinko_count_24h,
#         "total_games_24h": spins_count_24h + upgrades_count_24h + plinko_count_24h,
#         "stars_24h": stars_24h_sum
#     }
#
#
# # 🔹 Статистика за последние 24ч (обновленная с играми и звездами)
# async def get_statistics_24h(session):
#     # Начало сегодняшнего дня по МСК (00:00)
#     today_start_utc = get_today_start_moscow_utc()
#
#     # Пользователи
#     users_data = await session.execute(
#         select(
#             func.count(User.telegram_id),
#             func.count(case((User.created_at >= today_start_utc, 1)))
#         )
#     )
#     total_users, new_users_24h = users_data.one()
#
#     # Ставки за 24ч
#     bets_24h_result = await session.execute(
#         select(
#             func.coalesce(func.sum(Bet.amount_cents), cast(0, BigInteger)).label("bets_sum"),
#             func.coalesce(func.sum(case((Bet.cashed_out == True, Bet.win_cents), else_=0)), cast(0, BigInteger)).label(
#                 "wins_sum"),
#             func.coalesce(func.avg(case((Bet.cashed_out == True, Bet.cashout_multiplier_bp), else_=None)), 0).label(
#                 "avg_multiplier"),
#             func.count(Bet.id).label("bets_count"),
#             func.count(case((Bet.cashed_out == True, 1))).label("wins_count")
#         )
#         .where(Bet.created_at >= today_start_utc)
#     )
#     bets_24h = bets_24h_result.one()
#     bets_sum = bets_24h.bets_sum
#     wins_sum = bets_24h.wins_sum
#     avg_multiplier = (bets_24h.avg_multiplier or 0) / 100  # bp → множитель
#     bets_count = bets_24h.bets_count
#     wins_count = bets_24h.wins_count
#
#     # RTP = выигрыш / ставки * 100
#     rtp = (wins_sum / bets_sum * 100) if bets_sum > 0 else 0
#     profit_total = bets_sum - wins_sum
#     profit_label = "Прибыль" if profit_total >= 0 else "Убыток"
#
#     # Транзакции подарками за 24ч
#     gift_tx_result = await session.execute(
#         select(
#             func.count().label("gift_count"),
#             func.coalesce(func.sum(case((UserTransaction.currency == 'gift', UserTransaction.amount), else_=0)),
#                           0).label("gift_sum")
#         )
#         .where(UserTransaction.created_at >= today_start_utc)
#         .where(UserTransaction.currency == 'gift')
#     )
#     gift_tx = gift_tx_result.one()
#     gift_count = gift_tx.gift_count
#     gift_sum = gift_tx.gift_sum
#
#     # Статистика по играм за 24ч
#     games_24h = await get_games_statistics_24h(session)
#
#     # Статистика по играм за все время
#     games_all_time = await get_games_statistics_all_time(session)
#
#     return {
#         "users": {"total": total_users, "new_24h": new_users_24h},
#         "bets": {
#             "bets_sum": round(bets_sum / 100, 2),
#             "wins_sum": round(wins_sum / 100, 2),
#             "bets_count": bets_count,
#             "wins_count": wins_count,
#             "profit": round(profit_total / 100, 2),
#             "profit_label": profit_label,
#             "avg_multiplier": round(avg_multiplier, 2),
#             "rtp": round(rtp, 2)
#         },
#         "gifts": {
#             "gift_count": gift_count,
#             "gift_sum": round(gift_sum / 100, 2)
#         },
#         "games_24h": games_24h,
#         "games_all_time": games_all_time
#     }
#
#
# # 🔹 Самый крупный выигрыш за 24ч
# async def get_biggest_win_24h(session):
#     # Начало сегодняшнего дня по МСК (00:00)
#     today_start_utc = get_today_start_moscow_utc()
#     stmt = (
#         select(
#             User.telegram_id,
#             User.username,
#             User.first_name,
#             (Bet.win_cents - Bet.amount_cents).label("profit")
#         )
#         .join(User, Bet.user_id == User.telegram_id)
#         .where(and_(Bet.cashed_out == True, Bet.created_at >= today_start_utc))
#         .order_by(desc("profit"))
#         .limit(1)
#     )
#     result = await session.execute(stmt)
#     row = result.first()
#     if not row:
#         return None
#     return {
#         "telegram_id": row.telegram_id,
#         "username": row.username,
#         "first_name": row.first_name,
#         "profit": round(row.profit / 100, 2)
#     }
#
#
# # 🔹 Онлайн пользователи
# async def get_online_users():
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get("https://rocket-app.link/api/online-users-count") as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     return data.get("online_users", "N/A")
#     except Exception as e:
#         print(f"Error getting online users: {e}")
#     return "N/A"
#
#
# # 🔹 Отправка статистики админу (обновленная)
# async def send_admin_stats(message: Message, bot: Bot, session):
#     stats = await get_statistics_24h(session)
#     online_users = await get_online_users()
#     biggest_win = await get_biggest_win_24h(session)
#
#     # Форматирование информации о крупнейшем выигрыше
#     if biggest_win:
#         if biggest_win["username"]:
#             display = f"👤 <code>{biggest_win['telegram_id']}</code> @{biggest_win['username']}"
#         else:
#             display = f"👤 <code>{biggest_win['telegram_id']}</code> ({biggest_win['first_name'] or 'Без имени'})"
#         biggest_win_text = f"🎯 {display}\n💰 <b>{biggest_win['profit']} TON</b>"
#     else:
#         biggest_win_text = "❌ Нет выигравших за последние 24ч"
#
#     text = f"""
# 🏆 <b>СТАТИСТИКА ЗА 24 ЧАСА</b>
# ⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}
# {'=' * 35}
#
# 👥 <b>ПОЛЬЗОВАТЕЛИ</b>
# ├─ 📊 Всего: <b>{stats['users']['total']}</b>
# ├─ 🆕 Новые: <b>{stats['users']['new_24h']}</b>
# └─ 🌐 Онлайн в веб: <b>{online_users}</b>
#
# 🎰 <b>СТАВКИ</b>
# ├─ 📈 Количество ставок: <b>{stats['bets']['bets_count']}</b>
# ├─ ✅ Выигравших ставок: <b>{stats['bets']['wins_count']}</b>
# ├─ 💰 Сумма ставок: <b>{stats['bets']['bets_sum']} TON</b>
# ├─ 🏆 Сумма выигрышей: <b>{stats['bets']['wins_sum']} TON</b>
# ├─ 📊 {stats['bets']['profit_label']}: <b>{stats['bets']['profit']} TON</b>
# ├─ 🎯 Средний коэффициент: <b>{stats['bets']['avg_multiplier']}x</b>
# ├─ 📊 RTP: <b>{stats['bets']['rtp']}%</b>
#
# 🎮 <b>ИГРЫ ЗА 24Ч</b>
# ├─ 🎡 Кейсы: <b>{stats['games_24h']['spins_24h']}</b>
# ├─ ⚡ Апгрейды: <b>{stats['games_24h']['upgrades_24h']}</b>
# ├─ 🎯 Плинко: <b>{stats['games_24h']['plinko_24h']}</b>
# ├─ 📊 Всего игр: <b>{stats['games_24h']['total_games_24h']}</b>
# └─ ⭐ Звезд пополнено: <b>{stats['games_24h']['stars_24h']}</b>
#
# 🎮 <b>ИГРЫ ВСЕГО</b>
# ├─ 🎡 Кейсы: <b>{stats['games_all_time']['spins_total']}</b>
# ├─ ⚡ Апгрейды: <b>{stats['games_all_time']['upgrades_total']}</b>
# ├─ 🎯 Плинко: <b>{stats['games_all_time']['plinko_total']}</b>
# ├─ 📊 Всего игр: <b>{stats['games_all_time']['total_games']}</b>
# └─ ⭐ Звезд всего: <b>{stats['games_all_time']['total_stars']}</b>
#
# 🎁 <b>ПОДАРКИ ЗА 24Ч</b>
# ├─ Количество транзакций: <b>{stats['gifts']['gift_count']}</b>
# └─ Сумма подарков: <b>{stats['gifts']['gift_sum']} TON</b>
#
# 🚀 <b>КРУПНЕЙШИЙ ВЫИГРЫШ</b>
# {biggest_win_text}
# """
#
#     await message.answer(text, parse_mode="HTML")


from sqlalchemy import desc, func, cast, BigInteger, case, and_, select
import pytz
from datetime import datetime, timedelta, time
from aiogram import Bot
from aiogram.types import Message
import aiohttp

from bot.models.bets import Bet
from bot.models.user_transaction import UserTransaction
from bot.models.users import User
from bot.models.star_invoice import StarsInvoice
from bot.models.user_spins import UserSpin
from bot.models.user_gift_upgrades import UserGiftUpgrade
from bot.models.plinko_games import PlinkoGame
from bot.models.WheelSpin import WheelSpin  # Добавьте этот импорт

def get_today_start_moscow_utc():
    """Возвращает начало сегодняшнего дня по МСК в UTC"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)
    today_moscow = now_moscow.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_moscow.astimezone(pytz.UTC).replace(tzinfo=None)


# 🔹 Статистика по режимам за все время
async def get_games_statistics_all_time(session):
    # Кейсы (user_spins)
    spins_total = await session.execute(
        select(func.count(UserSpin.id))
    )
    spins_count = spins_total.scalar() or 0

    # Апгрейды подарков (user_gift_upgrades)
    upgrades_total = await session.execute(
        select(func.count(UserGiftUpgrade.id))
    )
    upgrades_count = upgrades_total.scalar() or 0

    # Plinko игры
    plinko_total = await session.execute(
        select(func.count(PlinkoGame.id))
    )
    plinko_count = plinko_total.scalar() or 0

    # Колесо фортуны (wheel_spins)
    wheel_total = await session.execute(
        select(func.count(WheelSpin.id))
    )
    wheel_count = wheel_total.scalar() or 0

    # Звезды всего пополнено
    stars_total = await session.execute(
        select(func.sum(StarsInvoice.amount))
        .where(StarsInvoice.status == 'paid')
    )
    total_stars = stars_total.scalar() or 0

    return {
        "spins_total": spins_count,
        "upgrades_total": upgrades_count,
        "plinko_total": plinko_count,
        "wheel_total": wheel_count,  # Добавлено
        "total_games": spins_count + upgrades_count + plinko_count + wheel_count,
        "total_stars": total_stars
    }


# 🔹 Статистика по режимам за последние 24ч
async def get_games_statistics_24h(session):
    # Начало сегодняшнего дня по МСК (00:00)
    today_start_utc = get_today_start_moscow_utc()

    # Кейсы за 24ч
    spins_24h = await session.execute(
        select(func.count(UserSpin.id))
        .where(UserSpin.created_at >= today_start_utc)
    )
    spins_count_24h = spins_24h.scalar() or 0

    # Апгрейды подарков за 24ч
    upgrades_24h = await session.execute(
        select(func.count(UserGiftUpgrade.id))
        .where(UserGiftUpgrade.created_at >= today_start_utc)
    )
    upgrades_count_24h = upgrades_24h.scalar() or 0

    # Plinko игры за 24ч
    plinko_24h = await session.execute(
        select(func.count(PlinkoGame.id))
        .where(PlinkoGame.created_at >= today_start_utc)
    )
    plinko_count_24h = plinko_24h.scalar() or 0

    # Колесо фортуны за 24ч
    wheel_24h = await session.execute(
        select(func.count(WheelSpin.id))
        .where(WheelSpin.created_at >= today_start_utc)
    )
    wheel_count_24h = wheel_24h.scalar() or 0

    # Звезды пополнено за 24ч
    stars_24h = await session.execute(
        select(func.sum(StarsInvoice.amount))
        .where(and_(
            StarsInvoice.status == 'paid',
            StarsInvoice.created_at >= today_start_utc
        ))
    )
    stars_24h_sum = stars_24h.scalar() or 0

    return {
        "spins_24h": spins_count_24h,
        "upgrades_24h": upgrades_count_24h,
        "plinko_24h": plinko_count_24h,
        "wheel_24h": wheel_count_24h,  # Добавлено
        "total_games_24h": spins_count_24h + upgrades_count_24h + plinko_count_24h + wheel_count_24h,
        "stars_24h": stars_24h_sum
    }


# 🔹 Статистика за последние 24ч (обновленная с играми и звездами)
async def get_statistics_24h(session):
    # Начало сегодняшнего дня по МСК (00:00)
    today_start_utc = get_today_start_moscow_utc()

    # Пользователи
    users_data = await session.execute(
        select(
            func.count(User.telegram_id),
            func.count(case((User.created_at >= today_start_utc, 1)))
        )
    )
    total_users, new_users_24h = users_data.one()

    # Ставки за 24ч
    bets_24h_result = await session.execute(
        select(
            func.coalesce(func.sum(Bet.amount_cents), cast(0, BigInteger)).label("bets_sum"),
            func.coalesce(func.sum(case((Bet.cashed_out == True, Bet.win_cents), else_=0)), cast(0, BigInteger)).label(
                "wins_sum"),
            func.coalesce(func.avg(case((Bet.cashed_out == True, Bet.cashout_multiplier_bp), else_=None)), 0).label(
                "avg_multiplier"),
            func.count(Bet.id).label("bets_count"),
            func.count(case((Bet.cashed_out == True, 1))).label("wins_count")
        )
        .where(Bet.created_at >= today_start_utc)
    )
    bets_24h = bets_24h_result.one()
    bets_sum = bets_24h.bets_sum
    wins_sum = bets_24h.wins_sum
    avg_multiplier = (bets_24h.avg_multiplier or 0) / 100  # bp → множитель
    bets_count = bets_24h.bets_count
    wins_count = bets_24h.wins_count

    # RTP = выигрыш / ставки * 100
    rtp = (wins_sum / bets_sum * 100) if bets_sum > 0 else 0
    profit_total = bets_sum - wins_sum
    profit_label = "Прибыль" if profit_total >= 0 else "Убыток"

    # Транзакции подарками за 24ч
    gift_tx_result = await session.execute(
        select(
            func.count().label("gift_count"),
            func.coalesce(func.sum(case((UserTransaction.currency == 'gift', UserTransaction.amount), else_=0)),
                          0).label("gift_sum")
        )
        .where(UserTransaction.created_at >= today_start_utc)
        .where(UserTransaction.currency == 'gift')
    )
    gift_tx = gift_tx_result.one()
    gift_count = gift_tx.gift_count
    gift_sum = gift_tx.gift_sum

    # Статистика по играм за 24ч
    games_24h = await get_games_statistics_24h(session)

    # Статистика по играм за все время
    games_all_time = await get_games_statistics_all_time(session)

    return {
        "users": {"total": total_users, "new_24h": new_users_24h},
        "bets": {
            "bets_sum": round(bets_sum / 100, 2),
            "wins_sum": round(wins_sum / 100, 2),
            "bets_count": bets_count,
            "wins_count": wins_count,
            "profit": round(profit_total / 100, 2),
            "profit_label": profit_label,
            "avg_multiplier": round(avg_multiplier, 2),
            "rtp": round(rtp, 2)
        },
        "gifts": {
            "gift_count": gift_count,
            "gift_sum": round(gift_sum / 100, 2)
        },
        "games_24h": games_24h,
        "games_all_time": games_all_time
    }


# 🔹 Самый крупный выигрыш за 24ч
async def get_biggest_win_24h(session):
    # Начало сегодняшнего дня по МСК (00:00)
    today_start_utc = get_today_start_moscow_utc()
    stmt = (
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            (Bet.win_cents - Bet.amount_cents).label("profit")
        )
        .join(User, Bet.user_id == User.telegram_id)
        .where(and_(Bet.cashed_out == True, Bet.created_at >= today_start_utc))
        .order_by(desc("profit"))
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return {
        "telegram_id": row.telegram_id,
        "username": row.username,
        "first_name": row.first_name,
        "profit": round(row.profit / 100, 2)
    }


# 🔹 Онлайн пользователи
async def get_online_users():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://rocket-app.link/api/online-users-count") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("online_users", "N/A")
    except Exception as e:
        print(f"Error getting online users: {e}")
    return "N/A"


# 🔹 Отправка статистики админу (обновленная)
async def send_admin_stats(message: Message, bot: Bot, session):
    stats = await get_statistics_24h(session)
    online_users = await get_online_users()
    biggest_win = await get_biggest_win_24h(session)

    # Форматирование информации о крупнейшем выигрыше
    if biggest_win:
        if biggest_win["username"]:
            display = f"👤 <code>{biggest_win['telegram_id']}</code> @{biggest_win['username']}"
        else:
            display = f"👤 <code>{biggest_win['telegram_id']}</code> ({biggest_win['first_name'] or 'Без имени'})"
        biggest_win_text = f"🎯 {display}\n💰 <b>{biggest_win['profit']} TON</b>"
    else:
        biggest_win_text = "❌ Нет выигравших за последние 24ч"

    text = f"""
🏆 <b>СТАТИСТИКА ЗА 24 ЧАСА</b>
⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}
{'=' * 35}

👥 <b>ПОЛЬЗОВАТЕЛИ</b>
├─ 📊 Всего: <b>{stats['users']['total']}</b>
├─ 🆕 Новые: <b>{stats['users']['new_24h']}</b>
└─ 🌐 Онлайн в веб: <b>{online_users}</b>

🎰 <b>СТАВКИ</b>
├─ 📈 Количество ставок: <b>{stats['bets']['bets_count']}</b>
├─ ✅ Выигравших ставок: <b>{stats['bets']['wins_count']}</b>
├─ 💰 Сумма ставок: <b>{stats['bets']['bets_sum']} TON</b>
├─ 🏆 Сумма выигрышей: <b>{stats['bets']['wins_sum']} TON</b>
├─ 📊 {stats['bets']['profit_label']}: <b>{stats['bets']['profit']} TON</b>
├─ 🎯 Средний коэффициент: <b>{stats['bets']['avg_multiplier']}x</b>
├─ 📊 RTP: <b>{stats['bets']['rtp']}%</b>

🎮 <b>ИГРЫ ЗА 24Ч</b>
├─ 🎡 Кейсы: <b>{stats['games_24h']['spins_24h']}</b>
├─ ⚡ Апгрейды: <b>{stats['games_24h']['upgrades_24h']}</b>
├─ 🎯 Плинко: <b>{stats['games_24h']['plinko_24h']}</b>
├─ 🎪 Rocket Spin: <b>{stats['games_24h']['wheel_24h']}</b>
├─ 📊 Всего игр: <b>{stats['games_24h']['total_games_24h']}</b>
└─ ⭐ Звезд пополнено: <b>{stats['games_24h']['stars_24h']}</b>

🎮 <b>ИГРЫ ВСЕГО</b>
├─ 🎡 Кейсы: <b>{stats['games_all_time']['spins_total']}</b>
├─ ⚡ Апгрейды: <b>{stats['games_all_time']['upgrades_total']}</b>
├─ 🎯 Плинко: <b>{stats['games_all_time']['plinko_total']}</b>
├─ 🎪 Rocket Spin: <b>{stats['games_all_time']['wheel_total']}</b>
├─ 📊 Всего игр: <b>{stats['games_all_time']['total_games']}</b>
└─ ⭐ Звезд всего: <b>{stats['games_all_time']['total_stars']}</b>

🎁 <b>ПОДАРКИ ЗА 24Ч</b>
├─ Количество транзакций: <b>{stats['gifts']['gift_count']}</b>
└─ Сумма подарков: <b>{stats['gifts']['gift_sum']} TON</b>

🚀 <b>КРУПНЕЙШИЙ ВЫИГРЫШ</b>
{biggest_win_text}
"""

    await message.answer(text, parse_mode="HTML")