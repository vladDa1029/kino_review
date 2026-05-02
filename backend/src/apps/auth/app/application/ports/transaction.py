#  Пока что один файл может стоит сделать папку для этого нопока мало абстракцей

from abc import abstractmethod
from typing import Protocol


class TransactionManager(Protocol):
    """Протокол для абстрактных менеджеров."""

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
