from dataclasses import dataclass, field
from typing import List

from app.domain.entity.base import Image, Requisite, User
from app.domain.policy.active_user import ActiveUserPolicy
from app.domain.policy.image_ownership import ImageOwnershipPolicy
from app.domain.policy.ownership import OwnershipPolicy


@dataclass
class ImageService:
    active_user_policy: ActiveUserPolicy = field(default_factory=ActiveUserPolicy)
    owner_policy: OwnershipPolicy = field(default_factory=OwnershipPolicy)
    image_policy: ImageOwnershipPolicy = field(default_factory=ImageOwnershipPolicy)

    def add_image(
        self,
        user: User,
        requisite: Requisite,
        images: List[Image],
        image: Image,
    ) -> List[Image]:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, requisite.users_id)
        self.image_policy.check(requisite, image)
        images.append(image)
        return images

    def remove_image(
        self,
        user: User,
        requisite: Requisite,
        images: List[Image],
        image: Image,
    ) -> List[Image]:
        self.active_user_policy.check(user)
        self.owner_policy.check(user.oid, requisite.users_id)
        self.image_policy.check(requisite, image)
        images.remove(image)
        return images
