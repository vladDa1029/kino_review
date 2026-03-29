from taskiq import AsyncBroker

from app.bootstrap import create_task_manager
from app.config import get_settings


def create_taskiq_app() -> AsyncBroker:
    return create_task_manager(get_settings())


taskiq_broker: AsyncBroker = create_taskiq_app()
