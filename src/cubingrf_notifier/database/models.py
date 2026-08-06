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
    foundation for future per-user preferences (region, events, time).
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(64), nullable=True)
    notifications_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    # Interface language (two-letter code, see i18n.DEFAULT_LANGUAGE).
    language = Column(String(10), nullable=False, default="ru", server_default="ru")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # When the user last blocked the bot (or the bot could not reach them).
    # NULL means the user is currently active/reachable.
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    # The last time the user interacted with the bot; NULL if never seen.
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")
    regions = relationship("UserRegion", back_populates="user", cascade="all, delete-orphan")

class Competition(Base):
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(512), nullable=False)
    location = Column(String(255), nullable=True)
    date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    url = Column(String(1024), nullable=True)
    disciplines = Column(JSON, nullable=True)
    # Registration availability: 'open' | 'scheduled' | 'closed' | None (unknown).
    reg_status = Column(String(20), nullable=True)
    # When registration opens (tz-aware UTC; None when the site gives no time).
    registration_start_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notifications = relationship("Notification", back_populates="competition", cascade="all, delete-orphan")

class UserEvent(Base):
    """A single event the user wants to follow (normalized preference)."""
    __tablename__ = "user_events"
    __table_args__ = (
        UniqueConstraint("user_id", "event_code", name="uq_user_event"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_code = Column(String(20), nullable=False)

    user = relationship("User", back_populates="events")

class UserRegion(Base):
    """A single region the user wants to follow (normalized preference)."""
    __tablename__ = "user_regions"
    __table_args__ = (
        UniqueConstraint("user_id", "region_key", name="uq_user_region"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    region_key = Column(String(128), nullable=False)

    user = relationship("User", back_populates="regions")

class Notification(Base):
    """A notification already delivered to a user for a competition.

    ``kind`` distinguishes notification types ('new' for a newly found
    competition, 'reg_soon' for a "registration opens in 30 minutes" reminder).
    The unique constraint covers the kind so each type is sent at most once.
    """
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "competition_id", "kind", name="uq_notification_user_competition_kind"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    # 'new' | 'reg_soon' — see docstring above.
    kind = Column(String(20), nullable=False, default="new", server_default="new")
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications")
    competition = relationship("Competition", back_populates="notifications")
