import uuid
from pydantic import validator
from app.core.types import Base


class MediaEntity(Base):
    id: str
    blob_name: str
    url: str

    @validator("id", pre=True)
    def convert_uuid(cls, v):
        # id is a str instead of UUID because UUIDs aren't JSON-serializable by default,
        # so when SQLAlchemy tries to serialize it fails
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
