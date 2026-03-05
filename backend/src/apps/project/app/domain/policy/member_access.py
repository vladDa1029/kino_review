from app.domain.entities import ProjectMember
from app.domain.enums import ProjectMemberStatus, ProjectRole
from app.domain.errors.business import AccessDeniedError


class ActiveMemberPolicy:
    def check(self, actor: ProjectMember, *, action: str) -> None:
        if actor.status != ProjectMemberStatus.ACTIVE:
            raise AccessDeniedError(f"Only active members can {action}.")


class DirectorMemberPolicy:
    def __init__(self, active_member_policy: ActiveMemberPolicy | None = None) -> None:
        self._active_member_policy = active_member_policy or ActiveMemberPolicy()

    def check(self, actor: ProjectMember, *, action: str) -> None:
        self._active_member_policy.check(actor, action=action)
        if actor.role != ProjectRole.DIRECTOR:
            raise AccessDeniedError(f"Only DIRECTOR can {action}.")
