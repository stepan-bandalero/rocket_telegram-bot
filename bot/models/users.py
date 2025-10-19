from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, func, ForeignKey
from bot.db import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(Text, nullable=True)
    first_name = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True)
    ton_balance = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    referred_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)

    created_promos = relationship("PromoLink", backref="creator", foreign_keys="PromoLink.created_by")


    # Добавляем отношения
    referral_earnings_as_referrer = relationship(
        "ReferralEarning",
        foreign_keys="ReferralEarning.referrer_id",
        backref="referrer"
    )
    referral_earnings_as_referred = relationship(
        "ReferralEarning",
        foreign_keys="ReferralEarning.referred_user_id",
        backref="referred_user"
    )