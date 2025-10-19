from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from bot.db import Base


class PromoLink(Base):
    __tablename__ = "promo_links"

    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    referral_percentage = Column(Integer, nullable=False, default=40)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    referrals = relationship("PromoReferral", back_populates="promo", cascade="all, delete-orphan")


class PromoReferral(Base):
    __tablename__ = "promo_referrals"

    id = Column(Integer, primary_key=True)
    promo_id = Column(Integer, ForeignKey("promo_links.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    promo = relationship("PromoLink", back_populates="referrals")
    user = relationship("User", backref="promo_referrals")