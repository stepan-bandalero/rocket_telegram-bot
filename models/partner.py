from sqlalchemy import Column, String, Boolean, TIMESTAMP, Integer, ForeignKey, func
from sqlalchemy.orm import relationship
from db import Base

class PartnerRedirect(Base):
    __tablename__ = "partner_redirects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    link = Column(String, nullable=False)
    analytics_event = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    avatar_url = Column(String, nullable=True)

    requirements = relationship("PartnerRequirement", back_populates="partner", cascade="all, delete-orphan")


class PartnerRequirement(Base):
    __tablename__ = "partner_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_key = Column(String, nullable=False)  # 'free_lottery', 'free_case'
    partner_id = Column(String, ForeignKey("partner_redirects.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)

    partner = relationship("PartnerRedirect", back_populates="requirements")