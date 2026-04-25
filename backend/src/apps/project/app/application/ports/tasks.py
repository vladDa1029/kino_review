from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ScheduleShiftReportGenerationCommand:
    report_id: UUID


class ShiftReportTaskDispatcher(Protocol):
    async def schedule_generation(
        self,
        command: ScheduleShiftReportGenerationCommand,
    ) -> None:
        raise NotImplementedError
