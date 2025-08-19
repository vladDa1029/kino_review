from dataclasses import dataclass
from app.domain.exceptions.base import ApplicationExaption


@dataclass(
    eq=False,
)
class InvalidCredentialsExaption(ApplicationExaption):
    """Ошибка слоя use case.

    Raise message:
        message (str): Неверный логин или пароль.
    """

    def __post_init__(self):
        object.__setattr__(self, "message", f"Неверный логин или пароль.")


@dataclass(eq=False)
class UserAlreadyExistsExaption(ApplicationExaption):
    """Ошибка пользователь уже существует

    Raise message:
        message (str): Tакой аккаунт уже существует.
    """

    def __post_init__(self):
        object.__setattr__(self, "message", f"Tакой аккаунт уже существует.")
