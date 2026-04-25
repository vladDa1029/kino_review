from enum import IntEnum


class ProjectRole(IntEnum):
    DIRECTOR = 10
    PROP_MASTER = 20
    CAMERA = 30
    SOUND = 40
    LIGHT = 50
    ACTOR = 60


class ProjectStatus(IntEnum):
    ACTIVE = 10
    ARCHIVED = 20


class ProjectMemberStatus(IntEnum):
    INVITED = 0
    ACTIVE = 10
    REMOVED = 20


class ShiftStatus(IntEnum):
    DRAFT = 0
    PENDING_APPROVAL = 10
    APPROVED = 20
    CANCELLED = 30
    COMPLETED = 40


class ShiftParticipantStatus(IntEnum):
    INVITED = 0
    CONFIRMED = 10
    RESERVING = 15
    RESERVED = 20
    DECLINED = 30
    CANCELLED = 40
    RESERVE_FAILED = 50


class DocumentType(IntEnum):
    PLAN = 10
    SCENARIO = 20
    REPORT = 30


class DocumentStatus(IntEnum):
    ACTIVE = 10
    ARCHIVED = 20
    DELETED = 30


class ResourceRequestStatus(IntEnum):
    PENDING_OWNER = 0
    APPROVED_OWNER = 10
    RESERVING = 15
    RESERVED = 20
    REJECTED_OWNER = 30
    CANCELLED = 40
    RESERVE_FAILED = 50


class ShiftReportGenerationStatus(IntEnum):
    PENDING = 10
    COLLECTING_SNAPSHOT = 20
    RENDERING = 30
    READY = 40
    FAILED = 50
    ARCHIVED = 60


class ShiftReportActualityStatus(IntEnum):
    ACTUAL = 10
    STALE = 20
