from sqlalchemy import BigInteger, Boolean, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class CupsGame(Base):
    __tablename__ = "cups_games"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    bet: Mapped[int] = mapped_column(BigInteger, nullable=False)
    selected_cup: Mapped[int] = mapped_column(Integer, nullable=False)
    winning_cup: Mapped[int] = mapped_column(Integer, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payout: Mapped[int] = mapped_column(BigInteger, nullable=False)

    server_seed: Mapped[str] = mapped_column(Text, nullable=False)
    client_seed: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    gift_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="stars")