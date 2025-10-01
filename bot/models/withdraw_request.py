class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    address = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    tx_hash = Column(Text, nullable=True)
    error_text = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    retries = Column(Integer, nullable=False, server_default="0")