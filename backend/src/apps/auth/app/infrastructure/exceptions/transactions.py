from app.domain.exceptions.base import ApplicationExaption


# TODO: доделать ошибки
class CommitExaption(ApplicationExaption):
    error: str

    def __post_init__(self):
        object.__setattr__(
            self,
            "message",
            f"Произошла ошибка при коммите:\n{self.error}",
        )


class RollbackExaption(ApplicationExaption):
    error: str

    def __post_init__(self):
        object.__setattr__(
            self,
            "message",
            f"Произошла ошибка при откате:\n{self.error}",
        )
