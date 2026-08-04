from typing import Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.exc import IntegrityError

from .models import Competition, User, Notification, UserDiscipline
from ..competitions.models import CompetitionDTO

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

    async def get_user_disciplines(self, telegram_id: int) -> List[str]:
        """Discipline codes the user selected (empty if none/not registered)."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            return []
        q = (
            select(UserDiscipline.discipline_code)
            .where(UserDiscipline.user_id == user.id)
            .order_by(UserDiscipline.discipline_code)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def set_user_disciplines(self, telegram_id: int, codes: List[str]) -> None:
        """Replace the user's discipline selection with the given codes."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user is None:
            user = await self.create_user(telegram_id)
        await self.session.execute(delete(UserDiscipline).where(UserDiscipline.user_id == user.id))
        for code in codes:
            self.session.add(UserDiscipline(user_id=user.id, discipline_code=code))
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
            url=dto.url,
            disciplines=dto.disciplines or [],
            reg_status=dto.reg_status,
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
