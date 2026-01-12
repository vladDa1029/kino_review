from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entity.base import BaseId, Description, Spare_time, User
from app.domain.errors.aggregate import CrossingTimingError
from app.domain.errors.policy import (
    DescriptionIdentityError,
    DescriptionOwnershipError,
    OwnershipError,
    UserInactiveError,
)
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.description import DescriptionOwnershipPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.service.description_service import DescriptionService
from app.domain.service.free_time_service import FreeTimeService
from app.domain.specification.description_identity import DescriptionIdentitySpec
from app.domain.specification.time_overlap import NonOverlappingTimeSpec
from app.domain.value.email import Email
from app.domain.value.phone import Phone


def make_user(user_id: BaseId, is_active: bool = True) -> User:
    return User(
        oid=user_id,
        email=Email("user@example.com"),
        is_active=is_active,
        create_at=datetime(2024, 1, 1, 0, 0, 0),
    )


def make_description(desc_id: BaseId, user_id: BaseId) -> Description:
    return Description(
        oid=desc_id,
        user_id=user_id,
        username="user",
        phone=Phone("89001234567"),
    )


def make_spare_time(
    timing_id: BaseId,
    owner_id: BaseId,
    start_time: datetime,
    end_time: datetime,
) -> Spare_time:
    return Spare_time(
        oid=timing_id,
        obj=owner_id,
        start_time=start_time,
        end_time=end_time,
    )


def test_active_user_policy_allows_active_user():
    user = make_user(BaseId(uuid4()), is_active=True)
    ActiveUserPolicy().check(user)


def test_active_user_policy_blocks_inactive_user():
    user = make_user(BaseId(uuid4()), is_active=False)
    with pytest.raises(UserInactiveError):
        ActiveUserPolicy().check(user)


def test_ownership_policy_allows_owner():
    owner_id = BaseId(uuid4())
    OwnershipPolicy().check(owner_id, owner_id)


def test_ownership_policy_blocks_non_owner():
    owner_id = BaseId(uuid4())
    other_id = BaseId(uuid4())
    with pytest.raises(OwnershipError):
        OwnershipPolicy().check(owner_id, other_id)


def test_description_ownership_policy_allows_owner():
    user_id = BaseId(uuid4())
    user = make_user(user_id)
    description = make_description(BaseId(uuid4()), user_id)
    DescriptionOwnershipPolicy().check(user, description)


def test_description_ownership_policy_blocks_non_owner():
    user_id = BaseId(uuid4())
    user = make_user(user_id)
    description = make_description(BaseId(uuid4()), BaseId(uuid4()))
    with pytest.raises(DescriptionOwnershipError):
        DescriptionOwnershipPolicy().check(user, description)


def test_description_identity_spec_requires_matching_ids():
    user_id = BaseId(uuid4())
    desc_id = BaseId(uuid4())
    current = make_description(desc_id, user_id)
    candidate = make_description(desc_id, user_id)
    assert DescriptionIdentitySpec().is_satisfied(current, candidate) is True


def test_description_identity_spec_rejects_mismatch():
    user_id = BaseId(uuid4())
    current = make_description(BaseId(uuid4()), user_id)
    candidate = make_description(BaseId(uuid4()), user_id)
    assert DescriptionIdentitySpec().is_satisfied(current, candidate) is False


def test_non_overlapping_time_spec_allows_disjoint_ranges():
    spec = NonOverlappingTimeSpec()
    owner_id = BaseId(uuid4())
    existing = [
        make_spare_time(
            BaseId(uuid4()),
            owner_id,
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
        )
    ]
    new_timing = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 12, 0, 0),
        datetime(2024, 1, 1, 13, 0, 0),
    )
    assert spec.is_satisfied(new_timing, existing) is True


def test_non_overlapping_time_spec_rejects_overlap_and_touching():
    spec = NonOverlappingTimeSpec()
    owner_id = BaseId(uuid4())
    existing = [
        make_spare_time(
            BaseId(uuid4()),
            owner_id,
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
        )
    ]
    overlap = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 10, 30, 0),
        datetime(2024, 1, 1, 11, 30, 0),
    )
    touching = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 11, 0, 0),
        datetime(2024, 1, 1, 12, 0, 0),
    )
    assert spec.is_satisfied(overlap, existing) is False
    assert spec.is_satisfied(touching, existing) is False


def test_free_time_service_adds_timing_when_valid():
    service = FreeTimeService()
    owner_id = BaseId(uuid4())
    timings = []
    new_timing = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 10, 0, 0),
        datetime(2024, 1, 1, 12, 0, 0),
    )
    result = service.add_timing(owner_id, timings, new_timing)
    assert result == timings
    assert timings == [new_timing]


def test_free_time_service_rejects_overlap():
    service = FreeTimeService()
    owner_id = BaseId(uuid4())
    timings = [
        make_spare_time(
            BaseId(uuid4()),
            owner_id,
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
        )
    ]
    new_timing = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 11, 0, 0),
        datetime(2024, 1, 1, 13, 0, 0),
    )
    with pytest.raises(CrossingTimingError):
        service.add_timing(owner_id, timings, new_timing)


def test_free_time_service_rejects_owner_mismatch():
    service = FreeTimeService()
    owner_id = BaseId(uuid4())
    new_timing = make_spare_time(
        BaseId(uuid4()),
        BaseId(uuid4()),
        datetime(2024, 1, 1, 10, 0, 0),
        datetime(2024, 1, 1, 12, 0, 0),
    )
    with pytest.raises(OwnershipError):
        service.add_timing(owner_id, [], new_timing)


def test_description_service_updates_description():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    current = make_description(BaseId(uuid4()), user_id)
    new_description = make_description(current.oid, user_id)
    updated = service.change_description(user, current, new_description)
    assert updated == new_description


def test_description_service_blocks_inactive_user():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=False)
    current = make_description(BaseId(uuid4()), user_id)
    new_description = make_description(current.oid, user_id)
    with pytest.raises(UserInactiveError):
        service.change_description(user, current, new_description)


def test_description_service_blocks_wrong_owner():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    current = make_description(BaseId(uuid4()), BaseId(uuid4()))
    new_description = make_description(current.oid, current.user_id)
    with pytest.raises(DescriptionOwnershipError):
        service.change_description(user, current, new_description)


def test_description_service_blocks_identity_mismatch():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    current = make_description(BaseId(uuid4()), user_id)
    new_description = make_description(BaseId(uuid4()), user_id)
    with pytest.raises(DescriptionIdentityError):
        service.change_description(user, current, new_description)
