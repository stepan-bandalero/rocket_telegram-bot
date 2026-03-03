from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Integer, Boolean, CheckConstraint, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from bot.db import Base


class LotteryTicket(Base):
    __tablename__ = "lottery_tickets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lottery_id = Column(BigInteger, ForeignKey("lotteries.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    is_free = Column(Boolean, nullable=False)
    purchased_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Связи
    lottery = relationship("Lottery", back_populates="tickets")
    user = relationship("User", foreign_keys=[user_id])
    winner_entry = relationship("LotteryWinner", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
