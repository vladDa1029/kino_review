from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities import ProjectMember, Shift
from app.domain.enums import ProjectMemberStatus, ProjectRole, ShiftStatus
from app.domain.errors.business import AccessDeniedError
from app.domain.policy.member_access import ActiveMemberPolicy, DirectorMemberPolicy
from app.domain.specification import (
    EditableShiftSpecification,
    IntervalWithinShiftSpecification,
)
from app.domain.value_objects import TimeInterval


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def test_active_member_policy_rejects_inactive_actor() -> None:
    policy = ActiveMemberPolicy()
    now = now_utc()
    actor = ProjectMember(
        oid=uuid4(),
        project_id=uuid4(),
        user_id=uuid4(),
        role=ProjectRole.DIRECTOR,
        status=ProjectMemberStatus.INVITED,
        invited_by=uuid4(),
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(AccessDeniedError):
        policy.check(actor, action="manage shifts")


def test_director_policy_rejects_non_director_actor() -> None:
    policy = DirectorMemberPolicy()
    now = now_utc()
    actor = ProjectMember(
        oid=uuid4(),
        project_id=uuid4(),
        user_id=uuid4(),
        role=ProjectRole.ACTOR,
        status=ProjectMemberStatus.ACTIVE,
        invited_by=uuid4(),
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(AccessDeniedError):
        policy.check(actor, action="manage participants")


def test_editable_shift_specification_matches_expected_statuses() -> None:
    specification = EditableShiftSpecification()
    now = now_utc()
    editable_shift = Shift(
        oid=uuid4(),
        project_id=uuid4(),
        title="Draft shift",
        description="desc",
        start_time=now,
        end_time=now + timedelta(hours=2),
        created_by=uuid4(),
        status=ShiftStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    immutable_shift = Shift(
        oid=uuid4(),
        project_id=uuid4(),
        title="Approved shift",
        description="desc",
        start_time=now,
        end_time=now + timedelta(hours=2),
        created_by=uuid4(),
        status=ShiftStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    assert specification.is_satisfied(editable_shift) is True
    assert specification.is_satisfied(immutable_shift) is False


def test_interval_within_shift_specification() -> None:
    specification = IntervalWithinShiftSpecification()
    now = now_utc()
    shift = Shift(
        oid=uuid4(),
        project_id=uuid4(),
        title="Shift",
        description="desc",
        start_time=now,
        end_time=now + timedelta(hours=4),
        created_by=uuid4(),
        status=ShiftStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    inside = TimeInterval(start=now + timedelta(minutes=30), end=now + timedelta(hours=2))
    outside = TimeInterval(start=now - timedelta(minutes=15), end=now + timedelta(hours=1))

    assert specification.is_satisfied(shift, inside) is True
    assert specification.is_satisfied(shift, outside) is False
