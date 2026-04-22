from collections.abc import Iterable
from datetime import datetime

from app.application.ports.domain import ClockPort, ShiftReportRepository
from app.domain.entities import ShiftReport
from app.domain.enums import (
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftReportActualityStatus,
    ShiftReportGenerationStatus,
)

REPORT_IN_PROGRESS_STATUSES = {
    ShiftReportGenerationStatus.PENDING,
    ShiftReportGenerationStatus.COLLECTING_SNAPSHOT,
    ShiftReportGenerationStatus.RENDERING,
}

REPORT_INCLUDED_PARTICIPANT_STATUSES = {
    ShiftParticipantStatus.CONFIRMED,
    ShiftParticipantStatus.RESERVING,
    ShiftParticipantStatus.RESERVED,
}

REPORT_INCLUDED_RESOURCE_STATUSES = {
    ResourceRequestStatus.RESERVED,
}


def has_in_progress_report(reports: Iterable[ShiftReport]) -> bool:
    return any(report.generation_status in REPORT_IN_PROGRESS_STATUSES for report in reports)


def next_shift_report_version(reports: Iterable[ShiftReport]) -> int:
    return max((report.version for report in reports), default=0) + 1


async def mark_shift_reports_stale(
    *,
    shift_reports: ShiftReportRepository,
    clock: ClockPort,
    shift_id,
    reason: str,
) -> None:
    now = clock.now()
    for report in await shift_reports.list_by_shift(shift_id):
        if report.generation_status != ShiftReportGenerationStatus.READY:
            continue
        if report.actuality_status == ShiftReportActualityStatus.STALE:
            continue
        _mark_stale(report=report, now=now, reason=reason)
        await shift_reports.update(report)


def _mark_stale(*, report: ShiftReport, now: datetime, reason: str) -> None:
    report.actuality_status = ShiftReportActualityStatus.STALE
    report.stale_reason = reason
    report.stale_marked_at = now
    report.updated_at = now
