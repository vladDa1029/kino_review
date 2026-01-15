from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.constant import MIN_SPARE_TIME
from app.domain.entity.base import (
    BaseId,
    Camera,
    CameraTripod,
    Description,
    Image,
    Light,
    LightTripod,
    Microfon,
    Requisite,
    Sound,
    Spare_time,
    User,
)
from app.domain.errors.aggregate import CrossingTimingError
from app.domain.errors.availability import (
    AvailabilityNotFoundError,
    ReservationOverlapError,
    WindowStatusError,
)
from app.domain.errors.policy import (
    DescriptionAlreadyExistsError,
    DescriptionIdentityError,
    DescriptionOwnershipError,
    ImageOwnershipError,
    OwnershipError,
    ResourceLockedError,
    UserInactiveError,
)
from app.domain.errors.value import (
    AvailabilityStatusError,
    MinSpareTimeError,
    TimeRangeError,
)
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.description import DescriptionOwnershipPolicy
from app.domain.policy.image_ownership import ImageOwnershipPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.policy.resource_lock import ResourceUnlockedPolicy
from app.domain.policy.single_description import SingleDescriptionPolicy
from app.domain.service.availability_service import AvailabilityService
from app.domain.service.description_service import DescriptionService
from app.domain.service.equipment_service import EquipmentService
from app.domain.service.free_time_service import FreeTimeService
from app.domain.service.image_service import ImageService
from app.domain.specification.description_identity import DescriptionIdentitySpec
from app.domain.specification.time_overlap import NonOverlappingTimeSpec
from app.domain.specification.time_within import TimeWithinWindowSpec
from app.domain.value.email import Email
from app.domain.value.phone import Phone
from app.domain.value.status import AvailabilityStatus
from app.domain.value.time import Time


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
    status: str = "free",
) -> Spare_time:
    return Spare_time(
        oid=timing_id,
        obj=owner_id,
        start_time=start_time,
        end_time=end_time,
        status=AvailabilityStatus(status),
    )


def make_requisite(req_id: BaseId, user_id: BaseId) -> Requisite:
    return Requisite(
        oid=req_id,
        users_id=user_id,
        title="prop",
        description="desc",
        type="decor",
        size="m",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
    )


def make_image(img_id: BaseId, requisite_id: BaseId) -> Image:
    return Image(
        oid=img_id,
        requisite_id=requisite_id,
        file="file.jpg",
        title="image",
        storage_key="key",
        bucket="bucket",
        mime_type="image/jpeg",
        size=123,
        description="desc",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
    )


@pytest.mark.parametrize(
    ("is_active", "expected_exception"),
    [
        (True, None),
        (False, UserInactiveError),
    ],
)
def test_active_user_policy(is_active, expected_exception):
    user = make_user(BaseId(uuid4()), is_active=is_active)
    if expected_exception:
        with pytest.raises(expected_exception):
            ActiveUserPolicy().check(user)
    else:
        ActiveUserPolicy().check(user)


@pytest.mark.parametrize(
    ("owner_matches", "expected_exception"),
    [
        (True, None),
        (False, OwnershipError),
    ],
)
def test_ownership_policy(owner_matches, expected_exception):
    owner_id = BaseId(uuid4())
    target_id = owner_id if owner_matches else BaseId(uuid4())
    if expected_exception:
        with pytest.raises(expected_exception):
            OwnershipPolicy().check(owner_id, target_id)
    else:
        OwnershipPolicy().check(owner_id, target_id)


@pytest.mark.parametrize(
    ("belongs", "expected_exception"),
    [
        (True, None),
        (False, DescriptionOwnershipError),
    ],
)
def test_description_ownership_policy(belongs, expected_exception):
    user_id = BaseId(uuid4())
    user = make_user(user_id)
    description_user_id = user_id if belongs else BaseId(uuid4())
    description = make_description(BaseId(uuid4()), description_user_id)
    if expected_exception:
        with pytest.raises(expected_exception):
            DescriptionOwnershipPolicy().check(user, description)
    else:
        DescriptionOwnershipPolicy().check(user, description)


@pytest.mark.parametrize(
    ("same_oid", "same_user", "expected"),
    [
        (True, True, True),
        (False, True, False),
        (True, False, False),
    ],
)
def test_description_identity_spec(same_oid, same_user, expected):
    user_id = BaseId(uuid4())
    other_user_id = BaseId(uuid4())
    oid = BaseId(uuid4())
    current = make_description(oid, user_id)
    candidate = make_description(
        oid if same_oid else BaseId(uuid4()),
        user_id if same_user else other_user_id,
    )
    assert DescriptionIdentitySpec().is_satisfied(current, candidate) is expected


@pytest.mark.parametrize(
    ("has_existing", "expected_exception"),
    [
        (False, None),
        (True, DescriptionAlreadyExistsError),
    ],
)
def test_single_description_policy(has_existing, expected_exception):
    existing = None
    if has_existing:
        existing = make_description(BaseId(uuid4()), BaseId(uuid4()))
    if expected_exception:
        with pytest.raises(expected_exception):
            SingleDescriptionPolicy().check(existing)
    else:
        SingleDescriptionPolicy().check(existing)


@pytest.mark.parametrize(
    ("obj_statuses", "other_statuses", "expected_exception"),
    [
        (["free"], [], None),
        (["reserved"], [], ResourceLockedError),
        (["blocked"], [], ResourceLockedError),
        (["free"], ["reserved"], None),
        ([], ["blocked"], None),
    ],
)
def test_resource_unlocked_policy(obj_statuses, other_statuses, expected_exception):
    policy = ResourceUnlockedPolicy()
    obj_id = BaseId(uuid4())
    other_id = BaseId(uuid4())
    windows = []
    for status in obj_statuses:
        windows.append(
            make_spare_time(
                BaseId(uuid4()),
                obj_id,
                datetime(2024, 1, 1, 10, 0, 0),
                datetime(2024, 1, 1, 11, 0, 0),
                status=status,
            )
        )
    for status in other_statuses:
        windows.append(
            make_spare_time(
                BaseId(uuid4()),
                other_id,
                datetime(2024, 1, 1, 10, 0, 0),
                datetime(2024, 1, 1, 11, 0, 0),
                status=status,
            )
        )
    if expected_exception:
        with pytest.raises(expected_exception):
            policy.check(obj_id, windows)
    else:
        policy.check(obj_id, windows)


@pytest.mark.parametrize(
    ("matches", "expected_exception"),
    [
        (True, None),
        (False, ImageOwnershipError),
    ],
)
def test_image_ownership_policy(matches, expected_exception):
    policy = ImageOwnershipPolicy()
    user_id = BaseId(uuid4())
    requisite_id = BaseId(uuid4())
    requisite = make_requisite(requisite_id, user_id)
    image = make_image(BaseId(uuid4()), requisite_id if matches else BaseId(uuid4()))
    if expected_exception:
        with pytest.raises(expected_exception):
            policy.check(requisite, image)
    else:
        policy.check(requisite, image)


@pytest.mark.parametrize(
    ("new_start", "new_end", "expected"),
    [
        (datetime(2024, 1, 1, 12, 0, 0), datetime(2024, 1, 1, 13, 0, 0), True),
        (datetime(2024, 1, 1, 10, 30, 0), datetime(2024, 1, 1, 11, 30, 0), False),
        (datetime(2024, 1, 1, 11, 0, 0), datetime(2024, 1, 1, 12, 0, 0), False),
    ],
)
def test_non_overlapping_time_spec(new_start, new_end, expected):
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
        new_start,
        new_end,
    )
    assert spec.is_satisfied(new_timing, existing) is expected


@pytest.mark.parametrize(
    ("outer_start", "outer_end", "inner_start", "inner_end", "expected"),
    [
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            True,
        ),
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0),
            datetime(2024, 1, 1, 9, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            False,
        ),
    ],
)
def test_time_within_spec(outer_start, outer_end, inner_start, inner_end, expected):
    spec = TimeWithinWindowSpec()
    owner_id = BaseId(uuid4())
    outer = make_spare_time(BaseId(uuid4()), owner_id, outer_start, outer_end)
    inner = make_spare_time(BaseId(uuid4()), owner_id, inner_start, inner_end)
    assert spec.is_satisfied(outer, inner) is expected


@pytest.mark.parametrize(
    ("start", "end", "expected_exception"),
    [
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 0, 0) + MIN_SPARE_TIME,
            None,
        ),
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 9, 0, 0),
            TimeRangeError,
        ),
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 0, 0) + MIN_SPARE_TIME - timedelta(minutes=1),
            MinSpareTimeError,
        ),
    ],
)
def test_time_value_validation(start, end, expected_exception):
    if expected_exception:
        with pytest.raises(expected_exception):
            Time(start_time=start, end_time=end)
    else:
        Time(start_time=start, end_time=end)


@pytest.mark.parametrize(
    ("status_value", "expected_exception"),
    [
        ("free", None),
        ("reserved", None),
        ("blocked", None),
        ("unknown", AvailabilityStatusError),
    ],
)
def test_availability_status_validation(status_value, expected_exception):
    if expected_exception:
        with pytest.raises(expected_exception):
            AvailabilityStatus(status_value)
    else:
        AvailabilityStatus(status_value)


@pytest.mark.parametrize(
    ("is_active", "owner_matches", "overlap", "expected_exception"),
    [
        (True, True, False, None),
        (False, True, False, UserInactiveError),
        (True, False, False, OwnershipError),
        (True, True, True, CrossingTimingError),
    ],
)
def test_free_time_service(is_active, owner_matches, overlap, expected_exception):
    service = FreeTimeService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=is_active)
    owner_id = user_id if owner_matches else BaseId(uuid4())
    timings = []
    if overlap:
        timings.append(
            make_spare_time(
                BaseId(uuid4()),
                owner_id,
                datetime(2024, 1, 1, 10, 0, 0),
                datetime(2024, 1, 1, 12, 0, 0),
            )
        )
    new_timing = make_spare_time(
        BaseId(uuid4()),
        owner_id,
        datetime(2024, 1, 1, 11, 0, 0) if overlap else datetime(2024, 1, 1, 13, 0, 0),
        datetime(2024, 1, 1, 14, 0, 0),
    )

    if expected_exception:
        with pytest.raises(expected_exception):
            service.add_timing(user, timings, new_timing)
    else:
        service.add_timing(user, timings, new_timing)
        assert new_timing in timings


@pytest.mark.parametrize(
    ("is_active", "wrong_owner", "wrong_identity", "expected_exception"),
    [
        (False, False, False, UserInactiveError),
        (True, True, False, DescriptionOwnershipError),
        (True, False, True, DescriptionIdentityError),
    ],
)
def test_description_service_errors(
    is_active, wrong_owner, wrong_identity, expected_exception
):
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=is_active)
    current_owner = BaseId(uuid4()) if wrong_owner else user_id
    current = make_description(BaseId(uuid4()), current_owner)
    new_description = make_description(
        BaseId(uuid4()) if wrong_identity else current.oid,
        current.user_id,
    )
    with pytest.raises(expected_exception):
        service.change_description(user, current, new_description)


def test_description_service_updates_description():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    current = make_description(BaseId(uuid4()), user_id)
    new_description = make_description(current.oid, user_id)
    updated = service.change_description(user, current, new_description)
    assert updated == new_description


@pytest.mark.parametrize(
    ("is_active", "has_existing", "wrong_owner", "expected_exception"),
    [
        (False, False, False, UserInactiveError),
        (True, True, False, DescriptionAlreadyExistsError),
        (True, False, True, DescriptionOwnershipError),
    ],
)
def test_description_service_create_errors(
    is_active, has_existing, wrong_owner, expected_exception
):
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=is_active)
    existing = None
    if has_existing:
        existing = make_description(BaseId(uuid4()), user_id)
    new_user_id = BaseId(uuid4()) if wrong_owner else user_id
    new_description = make_description(BaseId(uuid4()), new_user_id)
    with pytest.raises(expected_exception):
        service.create_description(user, existing, new_description)


def test_description_service_creates_description():
    service = DescriptionService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    new_description = make_description(BaseId(uuid4()), user_id)
    created = service.create_description(user, None, new_description)
    assert created == new_description


@pytest.mark.parametrize(
    ("user_active", "owner_matches", "start", "end", "windows", "expected_exception"),
    [
        (
            False,
            True,
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            [],
            UserInactiveError,
        ),
        (
            True,
            False,
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            [],
            OwnershipError,
        ),
        (
            True,
            True,
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
            [],
            TimeRangeError,
        ),
        (
            True,
            True,
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            [],
            AvailabilityNotFoundError,
        ),
        (
            True,
            True,
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            [
                make_spare_time(
                    BaseId(uuid4()),
                    BaseId(uuid4()),
                    datetime(2024, 1, 1, 10, 0, 0),
                    datetime(2024, 1, 1, 14, 0, 0),
                    status="reserved",
                )
            ],
            WindowStatusError,
        ),
        (
            True,
            True,
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            [
                make_spare_time(
                    BaseId(uuid4()),
                    BaseId(uuid4()),
                    datetime(2024, 1, 1, 10, 0, 0),
                    datetime(2024, 1, 1, 14, 0, 0),
                    status="free",
                ),
                make_spare_time(
                    BaseId(uuid4()),
                    BaseId(uuid4()),
                    datetime(2024, 1, 1, 11, 0, 0),
                    datetime(2024, 1, 1, 12, 0, 0),
                    status="reserved",
                ),
            ],
            ReservationOverlapError,
        ),
    ],
)
def test_availability_service_errors(
    user_active, owner_matches, start, end, windows, expected_exception
):
    service = AvailabilityService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=user_active)
    owner_id = user_id if owner_matches else BaseId(uuid4())
    obj_id = BaseId(uuid4())

    for window in windows:
        window.obj = obj_id

    with pytest.raises(expected_exception):
        service.reserve(user, windows, owner_id, obj_id, start, end)


def test_availability_service_reserve_splits_window():
    service = AvailabilityService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    owner_id = user_id
    obj_id = BaseId(uuid4())
    windows = [
        make_spare_time(
            BaseId(uuid4()),
            obj_id,
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0),
            status="free",
        )
    ]

    result = service.reserve(
        user,
        windows,
        owner_id,
        obj_id,
        datetime(2024, 1, 1, 11, 0, 0),
        datetime(2024, 1, 1, 12, 0, 0),
    )

    segments = sorted(result, key=lambda window: window.start_time)
    assert [(seg.start_time, seg.end_time, str(seg.status)) for seg in segments] == [
        (
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
            "free",
        ),
        (
            datetime(2024, 1, 1, 11, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            "reserved",
        ),
        (
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 14, 0, 0),
            "free",
        ),
    ]


@pytest.mark.parametrize(
    (
        "method_name",
        "is_active",
        "owner_matches",
        "locked_statuses",
        "expected_exception",
    ),
    [
        ("create", True, True, [], None),
        ("create", False, True, [], UserInactiveError),
        ("create", True, False, [], OwnershipError),
        ("update", True, True, ["reserved"], ResourceLockedError),
        ("update", True, True, [], None),
        ("update", True, False, [], OwnershipError),
        ("delete", True, True, ["blocked"], ResourceLockedError),
        ("delete", True, True, [], None),
        ("delete", False, True, [], UserInactiveError),
    ],
)
def test_equipment_service(
    method_name,
    is_active,
    owner_matches,
    locked_statuses,
    expected_exception,
):
    service = EquipmentService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=is_active)
    owner_id = user_id if owner_matches else BaseId(uuid4())
    equipment = Microfon(
        oid=BaseId(uuid4()),
        users_id=owner_id,
        title="mic",
        description="desc",
        type="shotgun",
        create_at=datetime(2024, 1, 1, 10, 0, 0),
    )
    windows = [
        make_spare_time(
            BaseId(uuid4()),
            equipment.oid,
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 11, 0, 0),
            status=status,
        )
        for status in locked_statuses
    ]

    action = getattr(service, method_name)
    if expected_exception:
        with pytest.raises(expected_exception):
            if method_name == "create":
                action(user, equipment)
            else:
                action(user, equipment, windows)
    else:
        if method_name == "create":
            created = action(user, equipment)
            assert created == equipment
        elif method_name == "update":
            updated = action(user, equipment, windows)
            assert updated == equipment
        else:
            action(user, equipment, windows)


@pytest.mark.parametrize(
    ("is_active", "owner_matches", "image_matches", "expected_exception"),
    [
        (True, True, True, None),
        (False, True, True, UserInactiveError),
        (True, False, True, OwnershipError),
        (True, True, False, ImageOwnershipError),
    ],
)
def test_image_service_add(is_active, owner_matches, image_matches, expected_exception):
    service = ImageService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=is_active)
    owner_id = user_id if owner_matches else BaseId(uuid4())
    requisite = make_requisite(BaseId(uuid4()), owner_id)
    image = make_image(
        BaseId(uuid4()),
        requisite.oid if image_matches else BaseId(uuid4()),
    )
    images = []

    if expected_exception:
        with pytest.raises(expected_exception):
            service.add_image(user, requisite, images, image)
    else:
        result = service.add_image(user, requisite, images, image)
        assert result == [image]


def test_image_service_remove():
    service = ImageService()
    user_id = BaseId(uuid4())
    user = make_user(user_id, is_active=True)
    requisite = make_requisite(BaseId(uuid4()), user_id)
    image = make_image(BaseId(uuid4()), requisite.oid)
    images = [image]

    result = service.remove_image(user, requisite, images, image)
    assert result == []


@pytest.mark.parametrize(
    ("entity_cls", "kwargs"),
    [
        (
            Microfon,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "mic",
                "description": "desc",
                "type": "shotgun",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            Camera,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "cam",
                "description": "desc",
                "type": "dslr",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            CameraTripod,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "tripod",
                "description": "desc",
                "type": "fluid",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            Light,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "light",
                "description": "desc",
                "type": "led",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            LightTripod,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "stand",
                "description": "desc",
                "type": "c-stand",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            Sound,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "recorder",
                "description": "desc",
                "type": "field",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            Requisite,
            {
                "oid": BaseId(uuid4()),
                "users_id": BaseId(uuid4()),
                "title": "prop",
                "description": "desc",
                "type": "decor",
                "size": "m",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
        (
            Image,
            {
                "oid": BaseId(uuid4()),
                "requisite_id": BaseId(uuid4()),
                "file": "file.jpg",
                "title": "image",
                "storage_key": "key",
                "bucket": "bucket",
                "mime_type": "image/jpeg",
                "size": 123,
                "description": "desc",
                "create_at": datetime(2024, 1, 1, 10, 0, 0),
            },
        ),
    ],
)
def test_equipment_entities(entity_cls, kwargs):
    entity = entity_cls(**kwargs)
    for key, value in kwargs.items():
        assert getattr(entity, key) == value
