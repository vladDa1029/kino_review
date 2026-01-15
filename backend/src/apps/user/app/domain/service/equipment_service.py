from dataclasses import dataclass, field
from typing import Iterable, Protocol

from app.domain.entity.base import BaseId, Spare_time, User
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.ownership import OwnershipPolicy
from app.domain.policy.resource_lock import ResourceUnlockedPolicy


class OwnedEntity(Protocol):
    oid: BaseId
    users_id: BaseId


@dataclass
class EquipmentService:
    active_user_policy: ActiveUserPolicy = field(default_factory=ActiveUserPolicy)
    owner_policy: OwnershipPolicy = field(default_factory=OwnershipPolicy)
    unlocked_policy: ResourceUnlockedPolicy = field(default_factory=ResourceUnlockedPolicy)

    def create(self, user: User, equipment: OwnedEntity) -> OwnedEntity:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, equipment.users_id)
        return equipment

    def update(
        self,
        user: User,
        equipment: OwnedEntity,
        windows: Iterable[Spare_time],
    ) -> OwnedEntity:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, equipment.users_id)
        self.unlocked_policy.check(equipment.oid, windows)
        return equipment

    def delete(
        self,
        user: User,
        equipment: OwnedEntity,
        windows: Iterable[Spare_time],
    ) -> None:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, equipment.users_id)
        self.unlocked_policy.check(equipment.oid, windows)
