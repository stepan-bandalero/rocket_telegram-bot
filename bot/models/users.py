from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, func, ForeignKey
from bot.db import Base


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(Text, nullable=True)
    first_name = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True)
    ton_balance = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    referred_by = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
