from abc import abstractmethod
from typing import Generic, Protocol, TypeVar

Q = TypeVar("Q")
R = TypeVar("R")


class Query(Protocol):
    """Marker protocol for queries."""


class QueryHandler(Protocol, Generic[Q, R]):
    """Handler for query objects."""

    @abstractmethod
    async def __call__(self, query: Q) -> R:
        raise NotImplementedError
