from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState

from app.bootstrap import create_container, create_task_manager
from app.config import get_settings
from app.set_log import configure_logging

TASKIQ_CONTAINER_STATE_KEY = "taskiq_app_container"


async def startup(state: TaskiqState) -> None:  # noqa: ARG001
    return None


async def shutdown(state: TaskiqState) -> None:
    container = state.get(TASKIQ_CONTAINER_STATE_KEY)
    if isinstance(container, AsyncContainer):
        await container.close()


def create_worker_taskiq_app() -> AsyncBroker:
    settings = get_settings()
    configure_logging(settings.log)

    task_manager = create_task_manager(settings)
    container = create_container(settings, task_manager=task_manager)

    task_manager.state[TASKIQ_CONTAINER_STATE_KEY] = container
    task_manager.on_event(TaskiqEvents.WORKER_STARTUP)(startup)
    task_manager.on_event(TaskiqEvents.WORKER_SHUTDOWN)(shutdown)

    setup_dishka(container, broker=task_manager)
    return task_manager
