from app.domain.entity.base import Description


class DescriptionIdentitySpec:
    def is_satisfied(self, current: Description, candidate: Description) -> bool:
        return current.oid == candidate.oid and current.user_id == candidate.user_id
