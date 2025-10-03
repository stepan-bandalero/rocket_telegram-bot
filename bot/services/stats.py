from sqlalchemy import desc, func, cast, BigInteger, case, and_, select
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import Message
import aiohttp

from bot.models.bets import Bet
from bot.models.user_transaction import UserTransaction
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
            func.coalesce(func.avg(case((Bet.cashed_out == True, Bet.cashout_multiplier_bp), else_=None)), 0).label("avg_multiplier"),
            func.count(Bet.id).label("bets_count"),
            func.count(case((Bet.cashed_out == True, 1))).label("wins_count")
        )
        .where(Bet.created_at >= last_24h)
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
            func.coalesce(func.sum(case((UserTransaction.currency == 'gift', UserTransaction.amount), else_=0)), 0).label("gift_sum")
        )
        .where(UserTransaction.created_at >= last_24h)
        .where(UserTransaction.currency == 'gift')
    )
    gift_tx = gift_tx_result.one()
    gift_count = gift_tx.gift_count
    gift_sum = gift_tx.gift_sum

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
            "gift_sum": round(gift_sum / 100, 2)  # переводим из cents в TON
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
            async with session.get("https://rocket-app.top/api/online-users-count") as response:
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
{'='*35}

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
🎁 <b>ПОДАРКИ</b>
├─ Количество транзакций: <b>{stats['gifts']['gift_count']}</b>
└─ Сумма подарков: <b>{stats['gifts']['gift_sum']} TON</b>


🚀 <b>КРУПНЕЙШИЙ ВЫИГРЫШ</b>
{biggest_win_text}
"""

    await message.answer(text, parse_mode="HTML")
