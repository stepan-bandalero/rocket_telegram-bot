# import json
# from datetime import datetime, timedelta
#
# import aiohttp
# from aiogram import Bot
# from aiogram.types import Message
# from sqlalchemy import select, func, case, BigInteger, and_, cast
# from sqlalchemy.ext.asyncio import AsyncSession
# from bot.models.users import User
# from bot.models.bets import Bet
#
#
# # 🔹 Топ-5 пользователей по прибыли
# async def get_top_winners(session: AsyncSession):
#     profit_expr = func.coalesce(
#         func.sum(
#             case(
#                 (Bet.cashed_out == True, Bet.win_cents - Bet.amount_cents),
#                 else_=cast(0, BigInteger)
#             )
#         ),
#         cast(0, BigInteger)
#     )
#
#     stmt = (
#         select(
#             User.telegram_id,
#             User.username,
#             User.first_name,
#             profit_expr.label("profit")
#         )
#         .join(Bet, Bet.user_id == User.telegram_id)
#         .group_by(User.telegram_id, User.username, User.first_name)
#         .order_by(profit_expr.desc())
#         .limit(5)
#     )
#
#     result = await session.execute(stmt)
#     rows = result.all()
#     return [
#         {
#             "telegram_id": r.telegram_id,
#             "username": r.username,
#             "first_name": r.first_name,
#             "profit": round(r.profit / 100, 2)
#         }
#         for r in rows
#     ]
#
#
# # 🔹 Статистика пользователей и ставок
# async def get_statistics(session: AsyncSession):
#     last_24h = datetime.utcnow() - timedelta(hours=24)
#
#     # Пользователи
#     users_data = await session.execute(
#         select(
#             func.count(User.telegram_id),
#             func.count(case((User.created_at >= last_24h, 1)))
#         )
#     )
#     total_users, new_users_24h = users_data.one()
#
#     # Ставки и выигрыши
#     total_bet_amount_result = await session.execute(
#         select(func.coalesce(func.sum(Bet.amount_cents), cast(0, BigInteger)))
#     )
#     total_bet_amount = total_bet_amount_result.scalar() or 0
#
#     total_win_amount_result = await session.execute(
#         select(
#             func.coalesce(
#                 func.sum(
#                     case(
#                         (Bet.cashed_out == True, Bet.win_cents),
#                         else_=cast(0, BigInteger)
#                     )
#                 ),
#                 cast(0, BigInteger)
#             )
#         )
#     )
#     total_win_amount = total_win_amount_result.scalar() or 0
#
#     bet_amount_24h_result = await session.execute(
#         select(
#             func.coalesce(
#                 func.sum(
#                     case(
#                         (Bet.created_at >= last_24h, Bet.amount_cents),
#                         else_=cast(0, BigInteger)
#                     )
#                 ),
#                 cast(0, BigInteger)
#             )
#         )
#     )
#     bet_amount_24h = bet_amount_24h_result.scalar() or 0
#
#     win_amount_24h_result = await session.execute(
#         select(
#             func.coalesce(
#                 func.sum(
#                     case(
#                         (and_(Bet.cashed_out == True, Bet.created_at >= last_24h), Bet.win_cents),
#                         else_=cast(0, BigInteger)
#                     )
#                 ),
#                 cast(0, BigInteger)
#             )
#         )
#     )
#     win_amount_24h = win_amount_24h_result.scalar() or 0
#
#     profit_total = total_win_amount - total_bet_amount
#     profit_24h = win_amount_24h - bet_amount_24h
#
#     return {
#         "users": {"total": total_users, "new_24h": new_users_24h},
#         "bets": {
#             "total": {
#                 "wins_sum": round(total_win_amount / 100, 2),
#                 "bets_sum": round(total_bet_amount / 100, 2),
#                 "profit": round(profit_total / 100, 2),
#                 "profit_label": "Прибыль" if profit_total >= 0 else "Убыток"
#             },
#             "24h": {
#                 "wins_sum": round(win_amount_24h / 100, 2),
#                 "bets_sum": round(bet_amount_24h / 100, 2),
#                 "profit": round(profit_24h / 100, 2),
#                 "profit_label": "Прибыль" if profit_24h >= 0 else "Убыток"
#             }
#         }
#     }
#
#
# # 🔹 Топ-5 по количеству ставок
# async def get_top_bettors(session: AsyncSession):
#     stmt = (
#         select(
#             User.telegram_id,
#             User.username,
#             User.first_name,
#             func.count(Bet.id).label("bets_count")
#         )
#         .join(Bet, Bet.user_id == User.telegram_id)
#         .group_by(User.telegram_id, User.username, User.first_name)
#         .order_by(func.count(Bet.id).desc())
#         .limit(5)
#     )
#     result = await session.execute(stmt)
#     rows = result.all()
#     return [
#         {
#             "telegram_id": r.telegram_id,
#             "username": r.username,
#             "first_name": r.first_name,
#             "bets_count": r.bets_count
#         }
#         for r in rows
#     ]
#
#
# # 🔹 Получение онлайн-пользователей
# async def get_online_users():
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get("http://localhost:3001/online-users-count") as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     return data.get("online_users", "N/A")
#                 else:
#                     return "N/A"
#     except Exception as e:
#         print(f"Error getting online users: {e}")
#         return "N/A"
#
#
# # 🔹 Отправка статистики админу
# async def send_admin_stats(message: Message, bot: Bot, session: AsyncSession):
#     stats = await get_statistics(session)
#     online_users = await get_online_users()
#     top_winners = await get_top_winners(session)
#     top_bettors = await get_top_bettors(session)
#
#     # Формируем топ-5 по прибыли
#     top_winners_text = []
#     for u in top_winners:
#         if u["username"]:
#             display = f"@{u['username']}"
#         else:
#             display = f"{u['telegram_id']} ({u['first_name'] or 'N/A'})"
#         profit_display = f"+{u['profit']}" if u['profit'] > 0 else f"{u['profit']}"
#         top_winners_text.append(f"• {display} — 💰 {profit_display} TON")
#
#     # Формируем топ-5 по ставкам
#     top_bettors_text = []
#     for u in top_bettors:
#         if u["username"]:
#             display = f"@{u['username']}"
#         else:
#             display = f"{u['telegram_id']} ({u['first_name'] or 'N/A'})"
#         top_bettors_text.append(f"• {display} — 🎰 {u['bets_count']}")
#
#     text = f"""
# 📊 <b>Главная статистика</b>
#
# 👥 Пользователи
# • Всего: {stats['users']['total']}
# • Новые за 24ч: {stats['users']['new_24h']}
# • Онлайн в веб: {online_users}
#
# 🎰 Ставки
# • Всего выигрышей: {stats['bets']['total']['wins_sum']} TON
# • Всего ставок: {stats['bets']['total']['bets_sum']} TON
# • {stats['bets']['total']['profit_label']} за всё время: {stats['bets']['total']['profit']} TON
# • Выигрыши за 24ч: {stats['bets']['24h']['wins_sum']} TON
# • Ставки за 24ч: {stats['bets']['24h']['bets_sum']} TON
# • {stats['bets']['24h']['profit_label']} за 24ч: {stats['bets']['24h']['profit']} TON
#
# 🏆 Топ-5 по прибыли
# """ + "\n".join(top_winners_text) + "\n\n" + \
#            "🎲 Топ-5 по количеству ставок\n" + "\n".join(top_bettors_text)
#
#     await message.answer(text, parse_mode="HTML")


from sqlalchemy import desc, func, cast, BigInteger, case, and_, select
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import Message
import aiohttp

from bot.models.bets import Bet
from bot.models.users import User


# 🔹 Статистика за последние 24ч
async def get_statistics_24h(session):
    last_24h = datetime.utcnow() - timedelta(hours=24)

    # Пользователи
    users_data = await session.execute(
        select(
            func.count(User.telegram_id),
            func.count(case((User.created_at >= last_24h, 1)))
        )
    )
    total_users, new_users_24h = users_data.one()

    # Ставки за 24ч
    bets_24h_result = await session.execute(
        select(
            func.coalesce(func.sum(Bet.amount_cents), cast(0, BigInteger)).label("bets_sum"),
            func.coalesce(func.sum(case((Bet.cashed_out == True, Bet.win_cents), else_=0)), cast(0, BigInteger)).label("wins_sum"),
            func.coalesce(func.avg(case((Bet.cashed_out == True, Bet.cashout_multiplier_bp), else_=None)), 0).label("avg_multiplier")
        )
        .where(Bet.created_at >= last_24h)
    )
    bets_24h = bets_24h_result.one()
    bets_sum = bets_24h.bets_sum
    wins_sum = bets_24h.wins_sum
    avg_multiplier = (bets_24h.avg_multiplier or 0) / 1000  # предположим, что cashout_multiplier_bp в bp (1/1000)

    # RTP = выигрыш / ставки * 100
    rtp = (wins_sum / bets_sum * 100) if bets_sum > 0 else 0

    return {
        "users": {"total": total_users, "new_24h": new_users_24h},
        "bets": {
            "wins_sum": round(wins_sum / 100, 2),
            "bets_sum": round(bets_sum / 100, 2),
            "profit": round((wins_sum - bets_sum) / 100, 2),
            "profit_label": "Прибыль" if wins_sum - bets_sum >= 0 else "Убыток",
            "avg_multiplier": round(avg_multiplier, 2),
            "rtp": round(rtp, 2)
        }
    }

# 🔹 Самый крупный выигрыш за 24ч
async def get_biggest_win_24h(session):
    last_24h = datetime.utcnow() - timedelta(hours=24)
    stmt = (
        select(
            User.telegram_id,
            User.username,
            User.first_name,
            (Bet.win_cents - Bet.amount_cents).label("profit")
        )
        .join(User, Bet.user_id == User.telegram_id)
        .where(and_(Bet.cashed_out == True, Bet.created_at >= last_24h))
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
            async with session.get("http://localhost:3001/online-users-count") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("online_users", "N/A")
    except Exception as e:
        print(f"Error getting online users: {e}")
    return "N/A"

# 🔹 Отправка статистики админу
async def send_admin_stats(message: Message, bot: Bot, session):
    stats = await get_statistics_24h(session)
    online_users = await get_online_users()
    biggest_win = await get_biggest_win_24h(session)

    # Текст для крупнейшего выигрыша
    if biggest_win:
        if biggest_win["username"]:
            display = f"@{biggest_win['username']}"
        else:
            display = f"{biggest_win['telegram_id']} ({biggest_win['first_name'] or 'N/A'})"
        biggest_win_text = f"{display} — 💰 {biggest_win['profit']} TON"
    else:
        biggest_win_text = "Нет выигравших за последние 24ч"

    text = f"""
📊 <b>Статистика за последние 24ч</b>

👥 Пользователи
• Всего: {stats['users']['total']}
• Новые за 24ч: {stats['users']['new_24h']}
• Онлайн в веб: {online_users}

🎰 Ставки
• Всего выигрышей: {stats['bets']['wins_sum']} TON
• Всего ставок: {stats['bets']['bets_sum']} TON
• {stats['bets']['profit_label']}: {stats['bets']['profit']} TON
• Средний коэффициент кэшаута: {stats['bets']['avg_multiplier']}x
• RTP: {stats['bets']['rtp']}%

🏆 Крупнейший выигрыш за 24ч
{biggest_win_text}
"""

    await message.answer(text, parse_mode="HTML")
