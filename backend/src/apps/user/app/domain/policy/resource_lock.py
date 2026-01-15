from typing import Iterable

from app.domain.entity.base import BaseId, Spare_time
from app.domain.errors.policy import ResourceLockedError


class ResourceUnlockedPolicy:
    def check(self, obj_id: BaseId, windows: Iterable[Spare_time]) -> None:
        for window in windows:
            if window.obj != obj_id:
                continue
            if str(window.status) != "free":
                raise ResourceLockedError("Resource has reserved or blocked windows.")
