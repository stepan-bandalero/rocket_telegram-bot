from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Integer, Boolean, CheckConstraint, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base


class LotteryWinner(Base):
    __tablename__ = "lottery_winners"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lottery_id = Column(BigInteger, ForeignKey("lotteries.id", ondelete="CASCADE"), nullable=False)
    ticket_id = Column(BigInteger, ForeignKey("lottery_tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    winner_place = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Связи
    lottery = relationship("Lottery", back_populates="winners")
    ticket = relationship("LotteryTicket", back_populates="winner_entry")
    user = relationship("User", foreign_keys=[user_id])
