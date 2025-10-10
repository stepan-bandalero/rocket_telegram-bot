from sqlalchemy import Column, BigInteger, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserTransaction(Base):
    __tablename__ = "user_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)  # Telegram ID пользователя
    type = Column(Text, nullable=False)  # 'deposit' или 'withdrawal'
    currency = Column(Text, nullable=False)  # 'ton' или 'gift'
    amount = Column(BigInteger, nullable=False)  # в сотнях/нанотонах или целое число
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
