from uuid import UUID

from dishka import FromDishka
from dishka.integrations.taskiq import inject

from app.application.commands.reports import (
    ProcessShiftReportGenerationCommand,
    ProcessShiftReportGenerationHandler,
)

PROCESS_SHIFT_REPORT_TASK_NAME = "project.process_shift_report_generation"


@inject(patch_module=True)
async def process_shift_report_generation_task(
    *,
    report_id: str,
    handler: FromDishka[ProcessShiftReportGenerationHandler],
) -> None:
    await handler(
        ProcessShiftReportGenerationCommand(
            report_id=UUID(report_id),
        )
    )
