from abc import abstractmethod
from typing import Protocol
from uuid import uuid4

from app.domain.entity.base import BaseId


class AbstractGenerationID(Protocol):
    """Protocol for ID generators."""

    @abstractmethod
    def __call__(self) -> BaseId:
        raise NotImplementedError


class GenerationUUID(AbstractGenerationID):
    """Generate UUID-based identifiers."""

    def __call__(self) -> BaseId:
        return BaseId(uuid4())
