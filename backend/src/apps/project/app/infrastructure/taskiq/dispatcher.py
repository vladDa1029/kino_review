from taskiq import AsyncBroker

from app.application.ports.tasks import (
    ScheduleShiftReportGenerationCommand,
    ShiftReportTaskDispatcher,
)
from app.presentation.tasks import PROCESS_SHIFT_REPORT_TASK_NAME


class TaskiqShiftReportTaskDispatcher(ShiftReportTaskDispatcher):
    def __init__(self, *, broker: AsyncBroker) -> None:
        self._broker = broker

    async def schedule_generation(
        self,
        command: ScheduleShiftReportGenerationCommand,
    ) -> None:
        task = self._broker.find_task(PROCESS_SHIFT_REPORT_TASK_NAME)
        if task is None:
            raise RuntimeError(f"Task '{PROCESS_SHIFT_REPORT_TASK_NAME}' is not registered.")
        await task.kiq(report_id=str(command.report_id))
