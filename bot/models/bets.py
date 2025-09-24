from sqlalchemy import Column, String, BigInteger, Boolean, Integer, ForeignKey, TIMESTAMP, Text
from sqlalchemy.orm import relationship

from bot.db import Base


class Bet(Base):
    __tablename__ = "bets"

    id = Column(String, primary_key=True)
    round_id = Column(String, ForeignKey("rounds.id"))
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    amount_cents = Column(BigInteger, nullable=False)
    cashed_out = Column(Boolean, default=False)
    cashout_multiplier_bp = Column(Integer)
    win_cents = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True), default="now()")
    asset_type = Column(Text, default="FIAT")
    user_gift_id = Column(BigInteger, ForeignKey("user_gifts.id"))
    ton_nano = Column(BigInteger)
    locked_price_cents = Column(BigInteger)
    final_gift_id = Column(String, ForeignKey("gift_catalog.id"))
    final_gift_title = Column(Text)
    final_gift_image_url = Column(Text)


    user_gift = relationship("UserGift", back_populates="bets")  # <-- ссылка на UserGift
