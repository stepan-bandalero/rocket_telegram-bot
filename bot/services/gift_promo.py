# bot/services/gift_promo.py
import secrets
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.gift_promo import GiftPromo, GiftPromoUse
from bot.models.gift_catalog import GiftCatalog
from bot.models.users import User
from bot.models.user_gift import UserGift, GiftStatus
from bot.models.user_transaction import UserTransaction
from bot.utils.generate_code import generate_gift_promo_code  # путь на твой вкус



class GiftPromoService:

    @staticmethod
    async def create_promo(session: AsyncSession, gift_catalog_id: str, created_by: int, max_uses: int) -> GiftPromo:
        code = generate_gift_promo_code(8)

        promo = GiftPromo(
            code=code,
            gift_catalog_id=gift_catalog_id,
            created_by=created_by,
            max_uses=max_uses,
            uses_count=0,  # ← добавь для консистентности
            is_active=True
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo


    # @staticmethod
    # async def list_promos(session: AsyncSession):
    #     result = await session.execute(
    #         select(
    #             GiftPromo.id,
    #             GiftPromo.code,
    #             GiftPromo.max_uses,
    #             GiftPromo.is_active,
    #             GiftPromo.created_by,
    #             GiftPromo.created_at,
    #             GiftCatalog.title,
    #             func.count(GiftPromoUse.id).label("uses_count"),
    #             func.min(GiftPromoUse.used_at).label("first_use"),
    #             func.max(GiftPromoUse.used_at).label("last_use"),
    #         )
    #         .join(GiftCatalog, GiftCatalog.id == GiftPromo.gift_catalog_id)
    #         .outerjoin(GiftPromoUse, GiftPromoUse.promo_id == GiftPromo.id)
    #         .group_by(GiftPromo.id, GiftCatalog.title)
    #     )
    #
    #     promos = []
    #     for row in result.all():
    #         promos.append({
    #             "id": row.id,
    #             "code": row.code,
    #             "title": row.title,
    #             "max_uses": row.max_uses,
    #             "is_active": row.is_active,
    #             "created_by": row.created_by,
    #             "created_at": row.created_at,
    #             "uses_count": row.uses_count or 0,
    #             "first_use": row.first_use,
    #             "last_use": row.last_use,
    #         })
    #     return promos


    @staticmethod
    async def list_promos(session: AsyncSession):
        result = await session.execute(
            select(
                GiftPromo.id,
                GiftPromo.code,
                GiftPromo.max_uses,
                GiftPromo.uses_count,  # ← берем из самой таблицы
                GiftPromo.is_active,
                GiftPromo.created_by,
                GiftPromo.created_at,
                GiftCatalog.title,
                func.min(GiftPromoUse.used_at).label("first_use"),
                func.max(GiftPromoUse.used_at).label("last_use"),
            )
            .join(GiftCatalog, GiftCatalog.id == GiftPromo.gift_catalog_id)
            .outerjoin(GiftPromoUse, GiftPromoUse.promo_id == GiftPromo.id)
            .group_by(GiftPromo.id, GiftCatalog.title)
        )

        promos = []
        for row in result.all():
            promos.append({
                "id": row.id,
                "code": row.code,
                "title": row.title,
                "max_uses": row.max_uses,
                "uses_count": row.uses_count,  # ← теперь из таблицы
                "is_active": row.is_active,
                "created_by": row.created_by,
                "created_at": row.created_at,
                "first_use": row.first_use,
                "last_use": row.last_use,
            })
        return promos

