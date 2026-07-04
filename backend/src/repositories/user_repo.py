from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def create(self, username: str, hashed_pw: str, role: str = "viewer") -> User:
        user = User(username=username, hashed_password=hashed_pw, role=role)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user_id: str, **fields) -> Optional[User]:
        user = await self.get(user_id)
        if not user:
            return None
        for key, value in fields.items():
            setattr(user, key, value)
        await self.session.flush()
        return user

    async def set_active(self, user_id: str, is_active: bool) -> Optional[User]:
        return await self.update(user_id, is_active=is_active)

    async def delete(self, user_id: str) -> bool:
        user = await self.get(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.flush()
        return True
