from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, func
from .models import Competition, User, Notification
from ..competitions.models import CompetitionDTO

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

    async def list_users(self) -> List[User]:
        q = select(User)
        res = await self.session.execute(q)
        return res.scalars().all()

class CompetitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_competition(self, dto: CompetitionDTO) -> Competition:
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

    async def get_latest_competitions(self, limit: int = 10) -> List[Competition]:
        q = select(Competition).order_by(Competition.created_at.desc()).limit(limit)
        res = await self.session.execute(q)
        return res.scalars().all()

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
        notif = Notification(user_id=user_id, competition_id=competition_id)
        self.session.add(notif)
        await self.session.flush()
        return notif
