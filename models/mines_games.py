from sqlalchemy import BigInteger, Boolean, Integer, Text, DateTime, func, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MinesGame(Base):
    __tablename__ = "mines_games"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    bet: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)

    grid_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mines_count: Mapped[int] = mapped_column(Integer, nullable=False)

    opened_cells: Mapped[dict] = mapped_column(JSONB, nullable=False)
    mines_positions: Mapped[dict] = mapped_column(JSONB, nullable=False)

    safe_hits: Mapped[int] = mapped_column(Integer, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False)

    payout: Mapped[int] = mapped_column(Integer, nullable=False)

    server_seed: Mapped[str] = mapped_column(Text, nullable=False)
    client_seed: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now()
    )