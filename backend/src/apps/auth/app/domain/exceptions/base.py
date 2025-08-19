from dataclasses import dataclass, field


@dataclass(
    eq=False,
)
class ApplicationExaption(Exception):
    """Базовый класс для наследования ошибок.

    Для переопределения требуется вызвать `__post_init__` с помощью метола `object.__setattr__()`.

    Returns:
        __str__: Возвращает `message` как текст.
    """

    message: str = field(
        default="Произошла ошибка приложения, в слои бизнес логики", kw_only=True
    )

    def __str__(self) -> str:
        return self.message