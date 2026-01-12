from app.domain.entity.base import BaseId
from app.domain.errors.policy import OwnershipError


class OwnershipPolicy:
    def check(self, owner_id: BaseId, target_owner_id: BaseId) -> None:
        if owner_id != target_owner_id:
            raise OwnershipError("Owner mismatch.")
