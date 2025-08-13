from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
import re


from app.domain.exaptions.values import DomainFieldExaption, EmailExaption


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class BaseValueObject(ABC):
    """
    Base class for immutable value objects (VO) in the domain.
    - Defined by its attributes, which must also be immutable.

    For simple cases where immutability and additional behavior aren't required,
    consider using `NewType` from `typing` as a lightweight alternative
    to inheriting from this class.
    """

    def __post_init__(self) -> None:
        if not fields(self):
            raise DomainFieldExaption(f"{type(self).__name__}")

        self._validate()

    @abstractmethod
    def _validate(self) -> None:
        """
        Check that a value is valid to create this value object.
        """
        raise NotImplementedError

    @abstractmethod
    def __str__(self) -> str:
        """
        :return: returns a string representation of this value object.
        """
        raise NotImplementedError


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class Email(BaseValueObject):
    """Тип данных почты.

    Валидирует данные и проверяет на соответствие.
    """

    value: str

    def _validate(self):
        email_validate_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_validate_pattern, self.value):
            raise EmailExaption(self.value)

    def __str__(self):
        return str(self.value)
