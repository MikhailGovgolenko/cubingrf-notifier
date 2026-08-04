from typing import List, Optional
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    BigInteger,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    """A Telegram user subscribed to notifications.

    ``notifications_enabled`` acts as the master on/off switch and is a
    foundation for future per-user preferences (region, disciplines, time).
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    notifications_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(512), nullable=False)
    location = Column(String(255), nullable=True)
    date = Column(DateTime(timezone=True), nullable=True)
    url = Column(String(1024), nullable=True)
    disciplines = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notifications = relationship("Notification", back_populates="competition", cascade="all, delete-orphan")

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # A user should never receive the same competition twice.
        UniqueConstraint("user_id", "competition_id", name="uq_notification_user_competition"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications")
    competition = relationship("Competition", back_populates="notifications")
