from app.core.types import Base, ImageId


class ImageUploadResponse(Base):
    image_id: ImageId
