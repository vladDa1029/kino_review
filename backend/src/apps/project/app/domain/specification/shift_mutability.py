from app.domain.entities import Shift
from app.domain.enums import ShiftStatus


class EditableShiftSpecification:
    ALLOWED_STATUSES = frozenset({ShiftStatus.DRAFT, ShiftStatus.PENDING_APPROVAL})

    def is_satisfied(self, shift: Shift) -> bool:
        return shift.status in self.ALLOWED_STATUSES
