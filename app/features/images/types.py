from shared.api.base import Base
from shared.api.type_aliases import ImageId


class ImageUploadResponse(Base):
    image_id: ImageId
