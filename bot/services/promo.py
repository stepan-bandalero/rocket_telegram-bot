import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists
from bot.models.promo import PromoLink, PromoReferral
from bot.models.users import User
from bot.models.user_gift import UserGift


class PromoService:
    @staticmethod
    async def create_promo(session: AsyncSession, title: str, created_by: int) -> PromoLink:
        # генерируем уникальный код
        while True:
            code = secrets.token_hex(4)  # короткий уникальный код
            exists_query = await session.execute(
                select(PromoLink).where(PromoLink.code == code)
            )
            if not exists_query.scalar_one_or_none():
                break

        promo = PromoLink(code=code, title=title, created_by=created_by)
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo

    @staticmethod
    async def get_promos(session: AsyncSession):
        # считаем количество переходов и активных пользователей
        result = await session.execute(
            select(
                PromoLink.id,
                PromoLink.title,
                PromoLink.code,
                func.count(PromoReferral.id).label("referrals_count"),
                func.count(func.nullif(User.telegram_id, None)).label("users_count"),
            )
            .outerjoin(PromoReferral, PromoReferral.promo_id == PromoLink.id)
            .outerjoin(User, User.telegram_id == PromoReferral.user_id)
            .group_by(PromoLink.id)
        )
        promos = result.all()

        # для каждого промо считаем активных пользователей
        data = []
        for promo_id, title, code, referrals_count, users_count in promos:
            active_query = await session.execute(
                select(func.count())
                .select_from(User)
                .outerjoin(UserGift, UserGift.user_id == User.telegram_id)
                .where(
                    User.telegram_id.in_(
                        select(PromoReferral.user_id).where(PromoReferral.promo_id == promo_id)
                    ),
                    ((UserGift.id is not None) | (User.telegram_id.in_(
                        select(User.telegram_id).where(User.ton_balance > 0)
                    )))
                )
            )
            active_users = active_query.scalar() or 0

            data.append({
                "id": promo_id,
                "title": title,
                "code": code,
                "referrals_count": referrals_count,
                "active_users": active_users
            })
        return data

    @staticmethod
    async def delete_promo(session: AsyncSession, promo_id: int):
        promo = await session.get(PromoLink, promo_id)
        if promo:
            await session.delete(promo)
            await session.commit()
            return True
        return False
