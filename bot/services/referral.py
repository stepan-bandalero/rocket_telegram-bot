from __future__ import annotations

import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.users import User
from bot.models.promo import PromoLink, PromoReferral


async def process_referral(session: AsyncSession, new_user: User, payload: str | None):
    """
    Обрабатываем payload:
      - user_id (числовой) → личная рефка
      - promo_code (строка) → промо-ссылка
    """
    if not payload:
        return None, None

    if re.fullmatch(r"\d+", payload):  # личная ссылка
        referrer_id = int(payload)
        if referrer_id != new_user.telegram_id:
            # сохраняем referred_by в существующем объекте
            if not new_user.referred_by:
                new_user.referred_by = referrer_id
        return "user", referrer_id

    # промо-код
    stmt = select(PromoLink).where(PromoLink.code == payload)
    result = await session.execute(stmt)
    promo = result.scalar_one_or_none()
    if promo:
        referral = PromoReferral(promo_id=promo.id, user_id=new_user.telegram_id)
        session.add(referral)
        return "promo", promo.id

    return None, None

