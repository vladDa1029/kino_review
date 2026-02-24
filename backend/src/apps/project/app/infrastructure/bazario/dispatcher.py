from app.application.ports.dispatcher import EventDispatcher


class BazarioDispatcher(EventDispatcher):
    def __init__(self) -> None:
        import bazario

        self._router = bazario.Router()

    async def dispatch(self, topic: str, payload: dict) -> None:
        dispatcher = getattr(self._router, "dispatch", None)
        if dispatcher is None:
            raise RuntimeError("bazario.Router has no dispatch method.")
        await dispatcher(topic, payload)
