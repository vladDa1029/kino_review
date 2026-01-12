from app.domain.entity.base import Description, User
from app.domain.errors.policy import DescriptionOwnershipError


class DescriptionOwnershipPolicy:
    def check(self, user: User, description: Description) -> None:
        if description.user_id != user.oid:
            raise DescriptionOwnershipError("Description does not belong to user.")
