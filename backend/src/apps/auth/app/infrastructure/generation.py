from abc import abstractmethod
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.entities import BaseUserId


class AbstractGenerationID(Protocol):
    """Протокол для генератора типов данных"""

    @abstractmethod
    def __call__(self) -> BaseUserId:
        raise NotImplemented


class GenerationUUID(AbstractGenerationID):
    """Генератор UUID"""

    def __call__(self) -> BaseUserId:
        return uuid4()
