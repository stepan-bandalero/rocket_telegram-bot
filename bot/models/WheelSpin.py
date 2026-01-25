# wheel_spins.py
from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from bot.db import Base


class WheelSpin(Base):
    __tablename__ = "wheel_spins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    target_gift_id = Column(Text, ForeignKey("gift_catalog.id"), nullable=False)
    bet_amount_cents = Column(Integer, nullable=False)
    currency = Column(String(5), nullable=False)  # 'stars' или 'ton'
    success = Column(Boolean, nullable=False)
    chance = Column(Float, nullable=False)
    hash = Column(Text, nullable=False)
    salt = Column(Text, nullable=False)
    target_gift_price = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True))

    user = relationship("User")
    gift = relationship("GiftCatalog", foreign_keys=[target_gift_id])