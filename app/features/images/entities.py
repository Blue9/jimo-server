from app.core.types import Base, ImageId


class MediaEntity(Base):
    id: ImageId
    blob_name: str
    url: str
