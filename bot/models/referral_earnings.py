from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, ForeignKey, func
from bot.db import Base

class ReferralEarning(Base):
    __tablename__ = "referral_earnings"
    __table_args__ = {'extend_existing': True}  # Добавляем эту строку

    id = Column(Integer, primary_key=True)
    referrer_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    referred_user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)  # Сумма в копейках/центах
    source_type = Column(Text, nullable=False)  # 'gift_deposit' или 'ton_deposit'
    source_id = Column(BigInteger, nullable=True)  # ID исходной транзакции
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())