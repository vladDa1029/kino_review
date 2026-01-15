from typing import Optional

from app.domain.entity.base import Description
from app.domain.errors.policy import DescriptionAlreadyExistsError


class SingleDescriptionPolicy:
    def check(self, existing: Optional[Description]) -> None:
        if existing is not None:
            raise DescriptionAlreadyExistsError("User already has description.")
