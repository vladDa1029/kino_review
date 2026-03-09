from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities import ProjectMember, Shift
from app.domain.enums import (
    ProjectMemberStatus,
    ProjectRole,
    ShiftStatus,
)
from app.domain.errors.business import (
    AccessDeniedError,
    DomainInvariantError,
    StateTransitionError,
)
from app.domain.services.participants import ShiftParticipantService
from app.domain.services.project_membership import ProjectMembershipService
from app.domain.services.resource_requests import ResourceRequestService
from app.domain.value_objects import TimeInterval


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def build_director_member(project_id):
    now = utc_now()
    return ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=uuid4(),
        role=ProjectRole.DIRECTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=uuid4(),
        created_at=now,
        updated_at=now,
    )


def test_time_interval_invalid_raises() -> None:
    now = utc_now()
    with pytest.raises(DomainInvariantError):
        TimeInterval(start=now, end=now)


def test_project_membership_invite_requires_director() -> None:
    service = ProjectMembershipService()
    now = utc_now()
    project_id = uuid4()
    actor = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=uuid4(),
        role=ProjectRole.ACTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=uuid4(),
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(AccessDeniedError):
        service.invite_member(
            actor=actor,
            member_id=uuid4(),
            project_id=project_id,
            invited_user_id=uuid4(),
            invited_by=actor.user_id,
            role=ProjectRole.CAMERA,
            now=now,
            existing=None,
        )


def test_shift_participant_must_fit_shift_interval() -> None:
    service = ShiftParticipantService()
    now = utc_now()
    project_id = uuid4()
    actor = build_director_member(project_id)
    shift = Shift(
        oid=uuid4(),
        project_id=project_id,
        title="Shift",
        description="desc",
        start_time=now,
        end_time=now + timedelta(hours=4),
        created_by=actor.user_id,
        status=ShiftStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(StateTransitionError):
        service.invite(
            actor=actor,
            shift=shift,
            participant_id=uuid4(),
            user_id=uuid4(),
            role=ProjectRole.CAMERA,
            time_from=now - timedelta(minutes=30),
            time_to=now + timedelta(hours=1),
            now=now,
            existing=None,
        )


def test_resource_request_create_requires_allowed_role() -> None:
    service = ResourceRequestService()
    now = utc_now()
    project_id = uuid4()
    actor = ProjectMember(
        oid=uuid4(),
        project_id=project_id,
        user_id=uuid4(),
        role=ProjectRole.ACTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    shift = Shift(
        oid=uuid4(),
        project_id=project_id,
        title="Shift",
        description="desc",
        start_time=now,
        end_time=now + timedelta(hours=3),
        created_by=uuid4(),
        status=ShiftStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(AccessDeniedError):
        service.create(
            actor=actor,
            request_id=uuid4(),
            shift=shift,
            resource_type="camera",
            resource_id=uuid4(),
            resource_owner_user_id=uuid4(),
            time_from=now,
            time_to=now + timedelta(hours=1),
            now=now,
        )
