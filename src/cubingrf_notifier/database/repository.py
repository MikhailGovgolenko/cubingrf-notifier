from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from .models import Competition, User, Notification
from ..competitions.models import CompetitionDTO

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

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        q = select(User).where(User.telegram_id == telegram_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def set_notifications_enabled(self, telegram_id: int, enabled: bool) -> Optional[User]:
        """Flip subscription on/off. Returns the user or None if not registered."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.notifications_enabled = enabled
        await self.session.flush()
        return user

    async def list_enabled_users(self) -> List[User]:
        """Users currently subscribed to notifications."""
        q = select(User).where(User.notifications_enabled.is_(True))
        res = await self.session.execute(q)
        return res.scalars().all()


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
            url=dto.url,
            disciplines=dto.disciplines or [],
        )
        self.session.add(comp)
        await self.session.flush()
        return comp

    async def exists_by_external_id(self, external_id: str) -> bool:
        q = select(func.count()).select_from(Competition).where(Competition.external_id == external_id)
        res = await self.session.execute(q)
        return res.scalar_one() > 0

    async def get_upcoming_competitions(self, offset: int = 0, limit: int = 10) -> List[Competition]:
        """Soonest future competitions first (only dates from today onwards)."""
        q = (
            select(Competition)
            .where(Competition.date >= func.current_date())
            .order_by(Competition.date.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def count_upcoming_competitions(self) -> int:
        """Total number of future competitions (for pagination)."""
        q = (
            select(func.count())
            .select_from(Competition)
            .where(Competition.date >= func.current_date())
        )
        res = await self.session.execute(q)
        return int(res.scalar_one())


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def was_sent(self, user_id: int, competition_id: int) -> bool:
        q = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.competition_id == competition_id,
        )
        res = await self.session.execute(q)
        return res.scalar_one() > 0

    async def mark_sent(self, user_id: int, competition_id: int) -> Notification:
        """Record that a notification was sent for a (user, competition) pair.

        The unique constraint on (user_id, competition_id) guarantees no
        duplicate notifications. A duplicate insert is rolled back via a
        savepoint so it never affects the surrounding transaction.
        """
        notif = Notification(user_id=user_id, competition_id=competition_id)
        try:
            async with self.session.begin_nested():
                self.session.add(notif)
        except IntegrityError:
            logger.info("Notification already sent for user %s, competition %s", user_id, competition_id)
        return notif
