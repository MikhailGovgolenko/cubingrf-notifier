from typing import Optional, List
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError

from .models import Competition, User, Notification, UserEvent, UserRegion
from ..competitions.availability import is_registration_available
from ..competitions.models import CompetitionDTO
from ..i18n import DEFAULT_LANGUAGE, get_user_language
from ..notifications.reminder_intervals import DEFAULT_REMINDER_INTERVAL

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, telegram_id: int) -> User:
        existing = await self.get_user_by_telegram_id(telegram_id)
        if existing:
            return existing
        user = User(telegram_id=telegram_id)
        self.session.add(user)
        await self.session.flush()
        return user

    async def register_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> User:
        """Register a user on first contact, saving their username and the
        interface language detected from Telegram. Existing users only get
        their username refreshed — a manually chosen language is preserved.
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                language=get_user_language(language_code),
                last_seen_at=func.now(),
            )
            self.session.add(user)
        elif username and user.username != username:
            user.username = username
        await self.session.flush()
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        q = select(User).where(User.telegram_id == telegram_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def sync_username(self, telegram_id: int, username: str) -> bool:
        """Persist ``username`` for an existing user when it changed.

        No-op (False) when the user is unknown or the value is unchanged or
        empty. Only touches ``username`` — never the chosen language.
        """
        if not username:
            return False
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None or user.username == username:
            return False
        user.username = username
        await self.session.flush()
        return True

    async def set_notifications_enabled(self, telegram_id: int, enabled: bool) -> Optional[User]:
        """Flip the master subscription switch on/off. Returns the user or None."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.notifications_enabled = enabled
        await self.session.flush()
        return user

    async def set_announcements_enabled(self, telegram_id: int, enabled: bool) -> Optional[User]:
        """Flip the competition-announcements switch. Returns the user or None."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.announcements_enabled = enabled
        await self.session.flush()
        return user

    async def set_registration_notifications_enabled(self, telegram_id: int, enabled: bool) -> Optional[User]:
        """Flip the registration-opening switch. Returns the user or None."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.registration_notifications_enabled = enabled
        await self.session.flush()
        return user

    async def set_reg_reminder_interval(self, telegram_id: int, minutes: int) -> Optional[User]:
        """Set how far in advance (minutes) to remind about registration.

        Returns None if the user is not registered.
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.reg_reminder_interval = minutes
        await self.session.flush()
        return user

    async def get_reg_reminder_interval(self, telegram_id: int) -> int:
        """The user's configured reminder interval in minutes (default if unset)."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None or user.reg_reminder_interval is None:
            return DEFAULT_REMINDER_INTERVAL
        return user.reg_reminder_interval

    async def set_blocked(self, telegram_id: int) -> bool:
        """Mark a user as blocked/offline (bot could not reach them).

        True only when the state actually changed, so callers know whether to
        commit. Never deletes the user.
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None or user.blocked_at is not None:
            return False
        user.blocked_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def mark_active(self, telegram_id: int) -> bool:
        """Reset a user back to active on any successful interaction.

        Clears ``blocked_at`` so the user is counted as active again. No-op
        (False) when the user is unknown or already active.
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None or user.blocked_at is None:
            return False
        user.blocked_at = None
        await self.session.flush()
        return True

    async def mark_seen(self, telegram_id: int, username: Optional[str] = None) -> bool:
        """Record activity for a user on any successful interaction.

        Updates ``last_seen_at`` to now, refreshes ``username`` when it changed
        (persistence only — never the chosen language), and clears ``blocked_at``
        so a previously blocked user is active again. Returns True when anything
        changed so callers know whether to commit.
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return False
        changed = False
        user.last_seen_at = func.now()
        changed = True
        if username and user.username != username:
            user.username = username
            changed = True
        if user.blocked_at is not None:
            user.blocked_at = None
            changed = True
        await self.session.flush()
        return changed

    async def get_user_language(self, telegram_id: int) -> str:
        """The user's interface language code (default language if unregistered)."""
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.language if user is not None else DEFAULT_LANGUAGE

    async def set_user_language(self, telegram_id: int, language: str) -> Optional[User]:
        """Save the user's interface language. Returns None if not registered."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.language = language
        await self.session.flush()
        return user

    async def list_enabled_users(self) -> List[User]:
        """Users currently subscribed and reachable by the bot.

        Blocked users (``blocked_at`` set) are excluded so we do not keep
        retrying delivery until they interact with the bot again.
        """
        q = select(User).where(
            User.notifications_enabled.is_(True),
            User.blocked_at.is_(None),
        )
        res = await self.session.execute(q)
        return res.scalars().all()

    async def get_user_events(self, telegram_id: int) -> List[str]:
        """Event codes the user selected (empty if none/not registered)."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []
        q = (
            select(UserEvent.event_code)
            .where(UserEvent.user_id == user.id)
            .order_by(UserEvent.event_code)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def set_user_events(self, telegram_id: int, codes: List[str]) -> None:
        """Replace the user's event selection with the given codes."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            user = await self.create_user(telegram_id)
        await self.session.execute(delete(UserEvent).where(UserEvent.user_id == user.id))
        for code in codes:
            self.session.add(UserEvent(user_id=user.id, event_code=code))
        await self.session.flush()

    async def get_user_regions(self, telegram_id: int) -> List[str]:
        """Region keys the user selected (empty if none/not registered)."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []
        q = (
            select(UserRegion.region_key)
            .where(UserRegion.user_id == user.id)
            .order_by(UserRegion.region_key)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def set_user_regions(self, telegram_id: int, keys: List[str]) -> None:
        """Replace the user's region selection with the given keys."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            user = await self.create_user(telegram_id)
        await self.session.execute(delete(UserRegion).where(UserRegion.user_id == user.id))
        for key in keys:
            self.session.add(UserRegion(user_id=user.id, region_key=key))
        await self.session.flush()


class CompetitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_competition(self, dto: CompetitionDTO) -> Competition:
        """Insert a new competition. Returns the persisted ORM with a real id.

        Raises IntegrityError if a competition with the same external_id
        already exists (races between the check and the insert).
        """
        comp = Competition(
            external_id=dto.external_id,
            name=dto.name,
            location=dto.location,
            date=dto.date,
            end_date=dto.end_date,
            url=dto.url,
            disciplines=dto.disciplines or [],
            reg_status=dto.reg_status,
            registration_start_at=dto.registration_start_at,
        )
        self.session.add(comp)
        await self.session.flush()
        return comp

    async def get_by_external_id(self, external_id: str) -> Optional[Competition]:
        """Find a competition by its site-specific id, or None."""
        q = select(Competition).where(Competition.external_id == external_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def exists_by_external_id(self, external_id: str) -> bool:
        q = select(func.count()).select_from(Competition).where(Competition.external_id == external_id)
        res = await self.session.execute(q)
        return res.scalar_one() > 0

    async def list_upcoming_competitions(self) -> List[Competition]:
        """Competitions the user could still register for.

        The date-driven rule from ``is_registration_available`` is the single
        source of truth: both actual dates (``date`` / ``end_date`` /
        ``registration_start_at``) and ``reg_status`` are considered, and a
        competition is shown only when registration is (or will be) open and
        the event has not started yet.
        """
        q = (
            select(Competition)
            .where(Competition.date.is_not(None))
            .order_by(Competition.date.asc())
        )
        res = await self.session.execute(q)
        comps = list(res.scalars().all())
        now = datetime.now(timezone.utc)
        return [c for c in comps if is_registration_available(c, now)]

    async def list_competitions_with_registration_start(self) -> List[Competition]:
        """Competitions that have a known registration opening moment.

        Filtering purely on the column; the "how far from now" check lives in
        the reminder logic so it stays unit-testable.
        """
        q = (
            select(Competition)
            .where(Competition.registration_start_at.is_not(None))
            .order_by(Competition.registration_start_at.asc())
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())


# Notification kinds stored in the notifications table.
KIND_NEW = "new"
KIND_REG_SOON = "reg_soon"


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def was_sent(self, user_id: int, competition_id: int, kind: str = KIND_NEW) -> bool:
        q = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.competition_id == competition_id,
            Notification.kind == kind,
        )
        res = await self.session.execute(q)
        return res.scalar_one() > 0

    async def mark_sent(self, user_id: int, competition_id: int, kind: str = KIND_NEW) -> Notification:
        """Record that a notification of the given kind was sent.

        The unique constraint on (user_id, competition_id, kind) guarantees no
        duplicate notifications per kind. A duplicate insert is rolled back via
        a savepoint so it never affects the surrounding transaction.
        """
        notif = Notification(user_id=user_id, competition_id=competition_id, kind=kind)
        try:
            async with self.session.begin_nested():
                self.session.add(notif)
        except IntegrityError:
            logger.info("Notification already sent for user %s, competition %s, kind %s", user_id, competition_id, kind)
        return notif
