from dataclasses import dataclass
from app.domain.exaptions.base import ApplicationExaption


@dataclass(eq=False)
class NoValidTokenExption(ApplicationExaption):
    ex: str

    def __post_init__(
        self,
    ):
        object.__setattr__(self, "message", f"Токен не валиден. {self.ex}")
