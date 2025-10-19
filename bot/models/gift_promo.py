# bot/models/gift_promo.py
from sqlalchemy import (
    Column, BigInteger, Text, TIMESTAMP, ForeignKey, func, Boolean, Integer
)
from sqlalchemy.orm import relationship
from bot.db import Base

class GiftPromo(Base):
    __tablename__ = "gift_promos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(Text, unique=True, nullable=False)
    gift_catalog_id = Column(Text, ForeignKey("gift_catalog.id"), nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    max_uses = Column(Integer, nullable=False)
    uses_count = Column(Integer, nullable=False, default=0)  # ← новое поле
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    uses = relationship("GiftPromoUse", back_populates="promo")
    gift = relationship("GiftCatalog")



class GiftPromoUse(Base):
    __tablename__ = "gift_promo_uses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    promo_id = Column(BigInteger, ForeignKey("gift_promos.id", ondelete="CASCADE"))
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    user_gift_id = Column(BigInteger, ForeignKey("user_gifts.id", ondelete="SET NULL"))
    used_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    promo = relationship("GiftPromo", back_populates="uses")
    user = relationship("User")
    user_gift = relationship("UserGift")  # ← связь с подарком

