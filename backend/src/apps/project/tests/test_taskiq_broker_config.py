from app.config import TaskIQ
from app.infrastructure.taskiq.broker import create_taskiq_broker


def test_taskiq_broker_uses_project_specific_transport_entities() -> None:
    settings = TaskIQ()

    broker = create_taskiq_broker("amqp://guest:guest@localhost:5672/", taskiq=settings)

    assert broker._exchange_name == "project.taskiq"
    assert broker._queue_name == "project.taskiq"
    assert broker._dead_letter_queue_name == "project.taskiq.dead_letter"
    assert broker._delay_queue_name == "project.taskiq.delay"
