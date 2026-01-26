from abc import abstractmethod
from typing import Generic, Protocol, TypeVar

C = TypeVar("C")


class Command(Protocol):
    """Marker protocol for commands."""


class CommandHandler(Protocol, Generic[C]):
    """Handler for command objects."""

    @abstractmethod
    async def __call__(self, command: C) -> None:
        raise NotImplementedError
