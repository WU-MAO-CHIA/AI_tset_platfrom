from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @abstractmethod
    async def get(self, id: str) -> T | None:
        pass

    @abstractmethod
    async def create(self, **kwargs) -> T:
        pass

    @abstractmethod
    async def update(self, id: str, **kwargs) -> T | None:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass
