#  Пока что один файл может стоит сделать папку для этого нопока мало абстракцей

from typing import Protocol
from abc import abstractmethod


class TransactionManager(Protocol):
    """Протокол для абстрактных менеджеров."""

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
