from app.domain.entity.base import User
from app.domain.errors.policy import UserInactiveError


# WARN: Не является проблемой этого сервиса странно проверять
class ActiveUserPolicy:
    def check(self, user: User) -> None:
        if not user.is_active:
            raise UserInactiveError("User is inactive.")
