import uuid
from pydantic import field_validator
from app.core.types import Base


class MediaEntity(Base):
    id: str
    blob_name: str
    url: str

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        # id is a str instead of UUID because UUIDs aren't JSON-serializable by default,
        # so when SQLAlchemy tries to serialize it fails
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
