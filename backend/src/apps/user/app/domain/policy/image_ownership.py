from app.domain.entity.base import Image, Requisite
from app.domain.errors.policy import ImageOwnershipError


class ImageOwnershipPolicy:
    def check(self, requisite: Requisite, image: Image) -> None:
        if image.requisite_id != requisite.oid:
            raise ImageOwnershipError("Image does not belong to requisite.")
