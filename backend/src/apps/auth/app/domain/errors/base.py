class ApplicationError(Exception):
    """Базовый класс для наследования ошибок."""

    def __init__(self, msg: str | None = None, *args: object) -> None:
        self.msg = msg
        if msg is None:
            super().__init__(*args)
        else:
            super().__init__(msg, *args)
