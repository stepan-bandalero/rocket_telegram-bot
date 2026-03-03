from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Integer, Boolean, CheckConstraint, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from bot.db import Base


class Lottery(Base):
    __tablename__ = "lotteries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Text, nullable=False)  # 'paid' или 'free'
    ticket_price_stars = Column(BigInteger, nullable=True)
    prize_gift_id = Column(Text, ForeignKey("gift_catalog.id"), nullable=False)
    winners_count = Column(Integer, nullable=False)
    results_date = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(Text, nullable=False, server_default="active")
    max_tickets_per_user = Column(Integer, nullable=True)
    max_total_tickets = Column(Integer, nullable=True)
    tickets_sold_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Связи
    tickets = relationship("LotteryTicket", back_populates="lottery", cascade="all, delete-orphan")
    winners = relationship("LotteryWinner", back_populates="lottery", cascade="all, delete-orphan")
    prize_gift = relationship("GiftCatalog", foreign_keys=[prize_gift_id])

