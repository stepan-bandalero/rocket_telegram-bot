from sqlalchemy import Column, Integer, BigInteger, Text, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import Any

from bot.db import Base


class Channel(Base):
    def __init__(self, **kw: Any):
        super().__init__(kw)

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    is_required = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    url = Column(Text, nullable=False)
