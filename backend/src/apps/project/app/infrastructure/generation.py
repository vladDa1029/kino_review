from abc import abstractmethod
from typing import Protocol
from uuid import UUID, uuid4


class AbstractGenerationID(Protocol):
    @abstractmethod
    def __call__(self) -> UUID:
        raise NotImplementedError


class GenerationUUID(AbstractGenerationID):
    def __call__(self) -> UUID:
        return uuid4()
