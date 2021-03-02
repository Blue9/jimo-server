import uuid

from app.schemas.base import Base


class ImageUploadResponse(Base):
    image_id: uuid.UUID
