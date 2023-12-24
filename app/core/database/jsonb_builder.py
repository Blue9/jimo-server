from app.core.database.models import ImageUploadRow
from app.features.images.entities import MediaEntity


def media_jsonb(images: list[ImageUploadRow]) -> list[dict]:
    return [MediaEntity.model_validate(image).model_dump() for image in images]
