from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import ENUM
from bot.db import Base


class GiftWithdrawal(Base):
    __tablename__ = "gift_withdrawals"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    user_gift_id = Column(Integer, ForeignKey("user_gifts.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False, server_default="pending")
    strategy = Column(Text, nullable=False, server_default="direct")
    retries = Column(Integer, nullable=False, server_default="0")
    error_text = Column(Text, nullable=True)
    portals_nft_id = Column(Text, nullable=True)
    purchase_price_cents = Column(Integer, nullable=True)
    withdrawn_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())