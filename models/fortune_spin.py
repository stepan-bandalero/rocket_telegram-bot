from sqlalchemy import Column, BigInteger, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import relationship
from db import Base

class FortuneSpin(Base):
    __tablename__ = "fortune_spins"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    mode_id = Column(Integer, nullable=False)
    spin_cost_cents = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)          # 'stars' или 'ton'
    won_gift_catalog_id = Column(String(255), ForeignKey("gift_catalog.id"), nullable=True)
    prize_index = Column(Integer, nullable=False)
    hash = Column(String(64), nullable=True)
    salt = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Связи
    user = relationship("User", foreign_keys=[user_id])
    gift = relationship("GiftCatalog", foreign_keys=[won_gift_catalog_id])