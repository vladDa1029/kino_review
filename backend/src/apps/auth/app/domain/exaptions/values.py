from dataclasses import dataclass

from app.domain.exaptions.base import ApplicationExaption


@dataclass(eq=False)
class DomainFieldExaption(ApplicationExaption):
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
class EmailExaption(ApplicationExaption):
    """Ошибка поча не валидна."""

    email: str

    def __post_init__(self):
        object.__setattr__(
            self,
            "message",
            f"Пароль не валидный {self.email}!",
        )
