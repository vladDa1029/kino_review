from dataclasses import dataclass
from app.domain.exaptions.base import ApplicationExaption

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
