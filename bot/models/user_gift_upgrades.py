from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from bot.db import Base


class UserGiftUpgrade(Base):
    __tablename__ = "user_gift_upgrades"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    from_gift_id = Column(BigInteger, ForeignKey("user_gifts.id"), nullable=False)
    target_gift_id = Column(Text, ForeignKey("gift_catalog.id"), nullable=False)
    success = Column(Boolean, nullable=False)
    chance = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True))
    hash = Column(Text)
    salt = Column(Text)

    user = relationship("User")