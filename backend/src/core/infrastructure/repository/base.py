from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, TypeVar

from src.core.domain.base import Base


BaseEntityType = TypeVar("BaseEntityType", bound=Base)


class BaseRepository(ABC):
    """
    Абстрактный класс от которого будут наследоваться все репозитории.
    Инкапсулирует логику запросов в базу данных.
    """

    @abstractmethod
    async def add(self, model: BaseEntityType) -> BaseEntityType:
        raise NotImplementedError

    @abstractmethod
    async def get(self, id: int) -> Optional[BaseEntityType]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, id: int, model: BaseEntityType) -> BaseEntityType:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list(self, start: int = 0, limit: int = 10) -> List[BaseEntityType]:
        raise NotImplementedError


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SqlalchemyBase(BaseRepository):
    """
    Класс для наследования. Проброшенна сессия.
    """

    def __init__(self, session: "AsyncSession") -> None:
        self._session = session
