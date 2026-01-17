# bot/models/broadcast_task.py
from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, JSON, func
from bot.db import Base


class BroadcastTask(Base):
    __tablename__ = "broadcast_tasks"

    id = Column(Integer, primary_key=True)
    content_type = Column(Text, nullable=False)  # text, photo, video, video_note
    text = Column(Text, nullable=True)
    media = Column(Text, nullable=True)  # URL или file_id
    buttons = Column(JSON, default=[])  # список dict {text, url|web_app}
    total = Column(Integer, default=0)
    sent = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    status = Column(Text, default="pending")  # pending, sending, stopped, done
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

