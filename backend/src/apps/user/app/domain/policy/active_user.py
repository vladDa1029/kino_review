from app.domain.entity.base import User
from app.domain.errors.policy import UserInactiveError


class ActiveUserPolicy:
    def check(self, user: User) -> None:
        if not user.is_active:
            raise UserInactiveError("User is inactive.")
