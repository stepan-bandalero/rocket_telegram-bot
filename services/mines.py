# services/mines.py (corrected)

from sqlalchemy import select, func, case, cast, Float, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from models.mines_games import MinesGame


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

                # extremes – COALESCE!
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
        }