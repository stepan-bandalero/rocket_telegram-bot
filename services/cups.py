from sqlalchemy import select, func, case, cast, Float, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession
from models.cups_games import CupsGame
from models.users import User  # модель пользователя (из вашего db)

class CupsAnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def global_stats(self):
        # ... без изменений (не содержит ни макс. ставок, ни X)
        q = await self.session.execute(
            select(
                func.count(CupsGame.id),
                func.count(distinct(CupsGame.user_id)),
                func.coalesce(func.sum(CupsGame.bet), 0),
                func.coalesce(func.sum(CupsGame.payout), 0),
                func.coalesce(func.avg(CupsGame.bet), 0),
                func.coalesce(func.avg(CupsGame.payout), 0),
                func.coalesce(func.max(CupsGame.payout), 0),
                func.coalesce(func.max(CupsGame.bet), 0),
                func.coalesce(
                    func.sum(case((CupsGame.won.is_(True), 1), else_=0)),
                    0
                ),
                func.coalesce(
                    func.avg(
                        cast(CupsGame.payout, Float) /
                        func.nullif(CupsGame.bet, 0)
                    ),
                    0
                ),
                func.coalesce(
                    func.max(
                        cast(CupsGame.payout, Float) /
                        func.nullif(CupsGame.bet, 0)
                    ),
                    0
                ),
                func.coalesce(func.stddev(CupsGame.payout), 0),
            )
        )

        (
            games, users, bets, payout,
            avg_bet, avg_payout,
            max_win, max_bet, wins,
            avg_mult, max_mult, volatility,
        ) = q.one()

        winrate = (wins / games * 100) if games else 0.0
        pnl = bets - payout
        rtp = (payout / bets * 100) if bets else 0.0

        return {
            "games": games,
            "users": users,
            "bets": bets,
            "payout": payout,
            "pnl": pnl,
            "winrate": winrate,
            "rtp": rtp,
            "avg_bet": avg_bet,
            "avg_payout": avg_payout,
            "max_win": max_win,
            "max_bet": max_bet,
            "avg_multiplier": avg_mult,
            "max_multiplier": max_mult,
            "volatility": volatility,
        }

    async def today_stats(self, start_ts):
        # Агрегаты за сегодня (без изменений)
        q = await self.session.execute(
            select(
                func.count(CupsGame.id),
                func.count(distinct(CupsGame.user_id)),
                func.coalesce(func.sum(CupsGame.bet), 0),
                func.coalesce(func.sum(CupsGame.payout), 0),
                func.coalesce(
                    func.sum(case((CupsGame.won.is_(True), 1), else_=0)),
                    0
                ),
                func.coalesce(func.avg(CupsGame.bet), 0),
                func.coalesce(func.avg(CupsGame.payout), 0),
                func.coalesce(func.max(CupsGame.payout), 0),
                func.coalesce(func.max(CupsGame.bet), 0),
                func.coalesce(
                    func.max(
                        cast(CupsGame.payout, Float) /
                        func.nullif(CupsGame.bet, 0)
                    ),
                    0
                ),
                func.coalesce(func.stddev(CupsGame.payout), 0),
            )
            .where(CupsGame.created_at >= start_ts)
        )

        (
            games, users, bets, payout, wins,
            avg_bet, avg_payout,
            max_win, max_bet, max_mult, volatility,
        ) = q.one()

        winrate = (wins / games * 100) if games else 0.0
        pnl = bets - payout
        rtp = (payout / bets * 100) if bets else 0.0

        # Топ-5 выигрышей за сегодня
        top_wins_query = (
            select(
                CupsGame.user_id,
                CupsGame.bet,
                CupsGame.payout,
                CupsGame.currency,
                CupsGame.gift_id,
                CupsGame.created_at,
                User.username,
                User.first_name,
            )
            .join(User, CupsGame.user_id == User.telegram_id)
            .where(CupsGame.created_at >= start_ts)
            .order_by(desc(CupsGame.payout))
            .limit(5)
        )
        top_wins_result = await self.session.execute(top_wins_query)
        top_wins = []
        for row in top_wins_result:
            top_wins.append({
                "user_id": row.user_id,
                "username": row.username or row.first_name or str(row.user_id),
                "bet": row.bet,
                "payout": row.payout,
                "currency": row.currency,
                "gift_id": row.gift_id,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            })

        return {
            "games": games,
            "users": users,
            "bets": bets,
            "payout": payout,
            "pnl": pnl,
            "winrate": winrate,
            "rtp": rtp,
            "avg_bet": avg_bet,
            "avg_payout": avg_payout,
            "max_win": max_win,
            "max_bet": max_bet,
            "max_multiplier": max_mult,
            "volatility": volatility,
            "top_wins": top_wins,
        }