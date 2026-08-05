from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.exc import IntegrityError

from .models import Competition, User, Notification, UserEvent, UserRegion
from ..competitions.models import CompetitionDTO
from ..i18n import DEFAULT_LANGUAGE, get_user_language

logger = logging.getLogger(__name__)

# Registration statuses that make a competition available to users.
OPEN_REG_STATUSES = ("open", "scheduled")


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
        """Flip subscription on/off. Returns the user or None if not registered."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.notifications_enabled = enabled
        await self.session.flush()
        return user

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
        """Users currently subscribed to notifications."""
        q = select(User).where(User.notifications_enabled.is_(True))
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
        """All future competitions with registration open or upcoming.

        Only future dates (from today onwards) where registration is NOT
        closed. Unknown status (NULL) is kept as a safe fallback so the list
        does not empty out if the site markup changes.
        """
        q = (
            select(Competition)
            .where(
                Competition.date >= func.current_date(),
                or_(
                    Competition.reg_status.is_(None),
                    Competition.reg_status.in_(OPEN_REG_STATUSES),
                ),
            )
            .order_by(Competition.date.asc())
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

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
