from sqlalchemy import Column, Text, BigInteger, Boolean
from sqlalchemy.orm import relationship
from bot.db import Base


class GiftCatalog(Base):
    __tablename__ = "gift_catalog"

    id = Column(Text, primary_key=True)
    tg_gift_slug = Column(Text, unique=True)
    title = Column(Text, nullable=False)
    price_cents = Column(BigInteger, nullable=False)
    image_url = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

