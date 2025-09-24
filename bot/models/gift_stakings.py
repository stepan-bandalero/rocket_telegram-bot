from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from bot.db import Base
from sqlalchemy.dialects.postgresql import ENUM
from datetime import datetime


class GiftStaking(Base):
    __tablename__ = "gift_stakings"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    user_gift_id = Column(BigInteger, ForeignKey("user_gifts.id"), unique=True)
    plan_id = Column(Text, ForeignKey("staking_plans.id"))
    principal_cents = Column(BigInteger, nullable=False)
    start_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    unlock_at = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(ENUM("ACTIVE", "CLAIMABLE", "CANCELLED", "WITHDRAWN", name="staking_status"), nullable=False, default="ACTIVE")
    accrued_cents = Column(BigInteger, nullable=False, default=0)
    last_accrual_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user_gift = relationship("UserGift")