from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, func
from sqlalchemy.orm import relationship
from bot.db import Base


class StarsInvoice(Base):
    __tablename__ = "stars_invoices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # payload уникален и нужен для идентификации платежа в Telegram
    payload = Column(Text, unique=True, nullable=False)

    # Telegram ID пользователя
    telegram_id = Column(BigInteger, nullable=False)

    # Количество звёзд
    amount = Column(BigInteger, nullable=False)

    # Статус: pending, paid, failed
    status = Column(Text, nullable=False, default="pending")

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Связь с пользователем
    user = relationship("User", primaryjoin="StarsInvoice.telegram_id==User.telegram_id", backref="stars_invoices")
