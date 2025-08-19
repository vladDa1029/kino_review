from abc import ABC
from dataclasses import dataclass
from typing import NewType
from uuid import UUID


BaseUserId = NewType("BaseUserId", UUID)


@dataclass
class Base(ABC):
    oid: BaseUserId

    def __eq__(self, other) -> bool:
        if isinstance(other, Base):
            return other.oid == self.oid
        return False

    def __hash__(self):
        return hash(self.oid)