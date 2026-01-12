from dataclasses import dataclass, field

from app.domain.entity.base import Description, User
from app.domain.errors.policy import DescriptionIdentityError
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.description import DescriptionOwnershipPolicy
from app.domain.specification.description_identity import DescriptionIdentitySpec


@dataclass
class DescriptionService:
    active_user_policy: ActiveUserPolicy = field(default_factory=ActiveUserPolicy)
    ownership_policy: DescriptionOwnershipPolicy = field(
        default_factory=DescriptionOwnershipPolicy
    )
    identity_spec: DescriptionIdentitySpec = field(default_factory=DescriptionIdentitySpec)

    def change_description(
        self,
        user: User,
        current: Description,
        new_description: Description,
    ) -> Description:
        self.active_user_policy.check(user)
        self.ownership_policy.check(user, current)
        if not self.identity_spec.is_satisfied(current, new_description):
            raise DescriptionIdentityError("Description identity mismatch.")
        return new_description
