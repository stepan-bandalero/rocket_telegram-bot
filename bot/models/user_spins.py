from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from bot.db import Base


class UserSpin(Base):
    __tablename__ = "user_spins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    case_id = Column(Text, nullable=False)
    prize_type = Column(Text, nullable=False)
    prize_title = Column(Text, nullable=False)
    prize_amount = Column(Numeric(20, 8), default=0)
    user_gift_id = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True))
    is_demo = Column(Boolean, default=False)

    user = relationship("User")