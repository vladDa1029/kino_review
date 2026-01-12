from dataclasses import dataclass
from typing import List
import warnings

from app.domain.entity.base import BaseId, Description, Spare_time, User
from app.domain.service.description_service import DescriptionService
from app.domain.service.free_time_service import FreeTimeService


@dataclass
class FreeTimeAggregate:
    user_id: BaseId
    spare_time_list: List[Spare_time]

    def addition_timing(self, new_timing: Spare_time) -> None:
        warnings.warn(
            "FreeTimeAggregate is deprecated; use FreeTimeService instead.",
            DeprecationWarning,
        )
        FreeTimeService().add_timing(self.user_id, self.spare_time_list, new_timing)


@dataclass
class AggregateUserDescrioption:
    user: User
    description: Description

    def change_descrption(self, new_description: Description) -> None:
        warnings.warn(
            "AggregateUserDescrioption is deprecated; use DescriptionService instead.",
            DeprecationWarning,
        )
        self.description = DescriptionService().change_description(
            self.user, self.description, new_description
        )
