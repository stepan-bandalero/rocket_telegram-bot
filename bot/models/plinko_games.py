from sqlalchemy import Column, Integer, BigInteger, String, Numeric, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from bot.db import Base


class PlinkoGame(Base):
    __tablename__ = "plinko_games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    mode = Column(String(10), nullable=False)
    bet_amount = Column(BigInteger, default=0)
    multiplier = Column(Numeric(5, 2), nullable=False)
    reward_type = Column(String(10), nullable=False)
    reward_amount = Column(BigInteger, default=0)
    won_gift_id = Column(BigInteger, ForeignKey("user_gifts.id"))
    created_at = Column(TIMESTAMP)

    user = relationship("User")