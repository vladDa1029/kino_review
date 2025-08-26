from dataclasses import dataclass
from app.domain.exceptions.base import ApplicationError


@dataclass(eq=False)
class DomainFieldError(ApplicationError):
    """Ошибка при отусутствия полей в Value Object.

    Args:
        name_class (str): имя класса.
    """

    name_class: str

    def __post_init__(self):
        object.__setattr__(
            self,
            "message",
            f"{self.name_class} должен содержвть хоть одно поле!",
        )

@dataclass(eq=False)
class EmailError(ApplicationError):
    """Ошибка поча не валидна."""

    value: str

    def __post_init__(self):
        object.__setattr__(
            self,
            "message",
            f"Пароль не валидный {self.value}!",
        )
