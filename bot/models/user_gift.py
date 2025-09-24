from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from bot.db import Base
from bot.models.gift_catalog import GiftCatalog



class UserGift(Base):
    __tablename__ = "user_gifts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True)
    gift_catalog_id = Column(Text, ForeignKey("gift_catalog.id"), nullable=True)
    received_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(Text, nullable=False, server_default="AVAILABLE")  # gift_status enum в БД
    locked_until = Column(TIMESTAMP(timezone=True), nullable=True)
    gift_image_url = Column(Text, nullable=True)
    price_cents = Column(BigInteger, nullable=False, server_default="0")

    # связи
    user = relationship("User", backref="gifts")
    gift_catalog = relationship(GiftCatalog, backref="user_gifts")
    bets = relationship("Bet", back_populates="user_gift")
    gift_stakings = relationship("GiftStaking", back_populates="user_gift")
