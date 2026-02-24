from typing import Protocol, TypeVar


TEntity = TypeVar("TEntity")


class Repository(Protocol[TEntity]):
    async def add(self, entity: TEntity) -> None:
        raise NotImplementedError

    async def get(self, reference) -> TEntity | None:
        raise NotImplementedError

    async def update(self, entity: TEntity) -> None:
        raise NotImplementedError

    async def delete(self, entity: TEntity) -> None:
        raise NotImplementedError
