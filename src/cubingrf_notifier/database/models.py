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
    # Independent per-type notification switches; both default to on so the
    # behaviour for existing users is unchanged. ``notifications_enabled``
    # stays as the master on/off switch (used by /start and /stop).
    announcements_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    registration_notifications_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    # User's CubingRF participant ID (RSF ID), e.g. "AS03". Manually entered,
    # no verification. NULL means round-result notifications cannot fire.
    rsf_id = Column(String(32), nullable=True)
    # Independent switch for round-result notifications. On by default so the
    # behaviour is consistent with the other per-type toggles; without an
    # ``rsf_id`` nothing is sent regardless of this flag.
    result_notifications_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    # How far in advance (minutes) to remind about an opening registration.
    # One of the values in REMINDER_INTERVALS; default 30 minutes.
    reg_reminder_interval = Column(Integer, nullable=False, default=30, server_default="30")
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
    # Registration availability: 'open' | 'scheduled' | 'closed' | 'cancelled' | None (unknown).
    reg_status = Column(String(20), nullable=True)
    # When registration opens (tz-aware UTC; None when the site gives no time).
    registration_start_at = Column(DateTime(timezone=True), nullable=True)
    # When the scraper first observed this competition as cancelled (tz-aware
    # UTC). Set exactly once; a cancelled competition stays visible to users
    # for 24 hours after this moment, then disappears. NULL means not (yet)
    # cancelled.
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
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

class RoundResultState(Base):
    """Persisted state for a single (user, competition, event, round) result.

    This is what lets the poller detect *new* results ("your round is
    finished") versus *changed* results ("your result was edited"), so it
    notifies only on real transitions, not on every poll.

    ``completed`` records whether the round has been seen as finished (all
    rostered participants have a recorded result). ``result_hash`` is a
    fingerprint of the user's current round snapshot; a different hash at a
    later poll means the result changed. When the round completes and the user
    has a result we notify; if ``result_hash`` changes afterwards we notify a
    smaller "edited" message.
    """
    __tablename__ = "round_result_states"
    __table_args__ = (
        UniqueConstraint("user_id", "competition_id", "event_code", "round_number", name="uq_rrs_user_competition_event_round"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=False)
    event_code = Column(String(20), nullable=False)
    round_number = Column(Integer, nullable=False)
    # Numeric per-competition registrant id of the user (from Data/registrant-id).
    registrant_id = Column(Integer, nullable=True)
    # Whether this round has been observed as finished for this user.
    completed = Column(Boolean, nullable=False, default=False, server_default="false")
    # When the round was first observed as finished (drives polling backoff).
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Do we need to report the *new* result (as opposed to only consistency runs)?
    notified = Column(Boolean, nullable=False, default=False, server_default="false")
    # Fingerprint of the user's current round snapshot (detects edits).
    result_hash = Column(String(64), nullable=True)
    # Last poll timestamp (used to back off polling of old/finished rounds).
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    competition = relationship("Competition")
