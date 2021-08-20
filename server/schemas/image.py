import uuid

from schemas.base import Base


class ImageUploadResponse(Base):
    image_id: uuid.UUID
