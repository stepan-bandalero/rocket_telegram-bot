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
            is_active=True
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo

    @staticmethod
    async def use_promo(session: AsyncSession, promo_code: str, user_id: int):
        # ищем промо
        stmt = select(GiftPromo).where(GiftPromo.code == promo_code, GiftPromo.is_active == True)
        result = await session.execute(stmt)
        promo = result.scalars().first()

        if not promo:
            return None, "❌ Промокод не найден или деактивирован"

        # считаем использований
        uses_count = await session.scalar(
            select(func.count()).where(GiftPromoUse.promo_id == promo.id)
        )

        if uses_count >= promo.max_uses:
            promo.is_active = False
            await session.commit()
            return None, "⚠ Промокод больше не действует — лимит исчерпан"

        # проверяем, использовал ли уже этот юзер
        existing_use = await session.scalar(
            select(GiftPromoUse).where(GiftPromoUse.promo_id == promo.id, GiftPromoUse.user_id == user_id)
        )
        if existing_use:
            return None, "🚫 Ты уже использовал этот промокод"

        # загружаем подарок
        gift = await session.get(GiftCatalog, promo.gift_catalog_id)
        if not gift or not gift.is_active:
            return None, "❌ Подарок недоступен"

        # выдаём подарок пользователю
        user_gift = UserGift(
            user_id=user_id,
            gift_catalog_id=gift.id,
            price_cents=gift.price_cents,
            status=GiftStatus.AVAILABLE,
            gift_image_url=gift.image_url,
            received_at=datetime.now(timezone.utc)
        )
        session.add(user_gift)
        await session.flush()

        # создаём транзакцию
        tx = UserTransaction(
            user_id=user_id,
            type="deposit",
            currency="gift",
            amount=gift.price_cents,
            created_at=datetime.now(timezone.utc)
        )
        session.add(tx)

        # записываем использование промокода
        use_entry = GiftPromoUse(promo_id=promo.id, user_id=user_id)
        session.add(use_entry)

        await session.commit()
        return gift, "🎁 Подарок успешно выдан!"

    @staticmethod
    async def list_promos(session: AsyncSession):
        result = await session.execute(
            select(
                GiftPromo.id,
                GiftPromo.code,
                GiftPromo.max_uses,
                GiftPromo.is_active,
                GiftPromo.created_by,
                GiftPromo.created_at,
                GiftCatalog.title,
                func.count(GiftPromoUse.id).label("uses_count"),
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
                "is_active": row.is_active,
                "created_by": row.created_by,
                "created_at": row.created_at,
                "uses_count": row.uses_count or 0,
                "first_use": row.first_use,
                "last_use": row.last_use,
            })
        return promos
