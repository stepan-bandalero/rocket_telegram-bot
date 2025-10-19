from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from bot.db import Base


class ReferralEarning(Base):
    __tablename__ = "referral_earnings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    referred_user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    source_type = Column(Text, nullable=False)
    source_id = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Добавьте эти отношения
    referrer = relationship("User", foreign_keys=[referrer_id], backref="referral_earnings_as_referrer")
    referred_user = relationship("User", foreign_keys=[referred_user_id], backref="referral_earnings_as_referred")