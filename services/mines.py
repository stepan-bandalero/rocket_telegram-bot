from sqlalchemy import select, func, case, cast, Float, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession
from models.mines_games import MinesGame
from models.users import User  # импорт вашей модели пользователей

class MinesAnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def global_stats(self):
        q = await self.session.execute(
            select(
                func.count(MinesGame.id),
                func.count(distinct(MinesGame.user_id)),
                # money totals
                func.coalesce(func.sum(MinesGame.bet), 0),
                func.coalesce(func.sum(MinesGame.payout), 0),
                # averages
                func.coalesce(func.avg(MinesGame.bet), 0),
                func.coalesce(func.avg(MinesGame.payout), 0),
                func.coalesce(func.avg(MinesGame.safe_hits), 0),
                func.coalesce(func.avg(MinesGame.mines_count), 0),
                func.coalesce(func.avg(MinesGame.grid_size), 0),
                # extremes – COALESCE!
                func.coalesce(func.max(MinesGame.payout), 0),
                func.coalesce(func.max(MinesGame.bet), 0),
                # wins
                func.coalesce(
                    func.sum(case((MinesGame.won.is_(True), 1), else_=0)),
                    0
                ),
                # multipliers
                func.coalesce(
                    func.avg(
                        cast(MinesGame.payout, Float) /
                        func.nullif(MinesGame.bet, 0)
                    ),
                    0
                ),
                func.coalesce(
                    func.max(
                        cast(MinesGame.payout, Float) /
                        func.nullif(MinesGame.bet, 0)
                    ),
                    0
                ),
                # volatility
                func.coalesce(func.stddev(MinesGame.payout), 0),
            )
        )

        (
            games, users, bets, payout,
            avg_bet, avg_payout, avg_safe_hits, avg_mines, avg_grid,
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
            "avg_safe_hits": avg_safe_hits,
            "avg_mines": avg_mines,
            "avg_grid": avg_grid,
            "max_win": max_win,
            "max_bet": max_bet,
            "avg_multiplier": avg_mult,
            "max_multiplier": max_mult,
            "volatility": volatility,
        }

    async def today_stats(self, start_ts):
        q = await self.session.execute(
            select(
                func.count(MinesGame.id),
                func.count(distinct(MinesGame.user_id)),
                func.coalesce(func.sum(MinesGame.bet), 0),
                func.coalesce(func.sum(MinesGame.payout), 0),
                func.coalesce(func.sum(case((MinesGame.won.is_(True), 1), else_=0)), 0),
                func.coalesce(func.avg(MinesGame.bet), 0),
                func.coalesce(func.avg(MinesGame.payout), 0),
                func.coalesce(func.avg(MinesGame.safe_hits), 0),
                func.coalesce(func.avg(MinesGame.mines_count), 0),
                func.coalesce(func.avg(MinesGame.grid_size), 0),
                func.coalesce(func.max(MinesGame.payout), 0),
                func.coalesce(func.max(MinesGame.bet), 0),
                func.coalesce(
                    func.max(cast(MinesGame.payout, Float) / func.nullif(MinesGame.bet, 0)),
                    0
                ),
                func.coalesce(func.stddev(MinesGame.payout), 0),
            )
            .where(MinesGame.created_at >= start_ts)
        )

        (
            games, users, bets, payout, wins,
            avg_bet, avg_payout, avg_safe_hits, avg_mines, avg_grid,
            max_win, max_bet, max_mult, volatility,
        ) = q.one()

        winrate = (wins / games * 100) if games else 0.0
        pnl = bets - payout
        rtp = (payout / bets * 100) if bets else 0.0

        # --- Топ-5 выигрышей за сегодня ---
        top_wins_query = (
            select(
                MinesGame.user_id,
                MinesGame.bet,
                MinesGame.payout,
                MinesGame.currency,
                MinesGame.created_at,
                User.username,
                User.first_name,
            )
            .join(User, MinesGame.user_id == User.telegram_id)
            .where(MinesGame.created_at >= start_ts)
            .order_by(desc(MinesGame.payout))
            .limit(5)
        )
        top_result = await self.session.execute(top_wins_query)
        top_wins = []
        for row in top_result:
            top_wins.append({
                "user_id": row.user_id,
                "username": row.username or row.first_name or str(row.user_id),
                "bet": row.bet,
                "payout": row.payout,
                "currency": row.currency,
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
            "avg_safe_hits": avg_safe_hits,
            "avg_mines": avg_mines,
            "avg_grid": avg_grid,
            "max_win": max_win,
            "max_bet": max_bet,
            "max_multiplier": max_mult,
            "volatility": volatility,
            "top_wins": top_wins,   # <-- новое поле
        }