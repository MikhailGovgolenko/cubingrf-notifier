from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Competition, User, Notification
from datetime import datetime
from ..competitions.models import CompetitionDTO

class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_competition_by_external_id(self, external_id: str) -> Optional[Competition]:
        q = select(Competition).where(Competition.external_id == external_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def add_competition(self, dto: CompetitionDTO) -> Competition:
        comp = Competition(
            external_id=dto.external_id,
            name=dto.name,
            location=dto.location,
            date=dto.date,
            url=dto.url,
            disciplines=','.join(dto.disciplines) if dto.disciplines else None,
        )
        self.session.add(comp)
        await self.session.flush()
        return comp

    async def add_user_if_not_exists(self, telegram_id: int) -> User:
        q = select(User).where(User.telegram_id == telegram_id)
        res = await self.session.execute(q)
        user = res.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id)
        self.session.add(user)
        await self.session.flush()
        return user

    async def add_notification(self, user_id: int, competition_id: int):
        notif = Notification(user_id=user_id, competition_id=competition_id)
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def get_subscribed_users(self) -> List[User]:
        q = select(User)
        res = await self.session.execute(q)
        return res.scalars().all()

    async def get_upcoming_competitions(self, limit: int = 10) -> List[Competition]:
        q = select(Competition).order_by(Competition.created_at.desc()).limit(limit)
        res = await self.session.execute(q)
        return res.scalars().all()
