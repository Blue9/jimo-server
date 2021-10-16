import uuid
from datetime import datetime
from typing import Optional

from shared.schemas.base import Base


# Only use internally, do not expose via endpoint
class InternalUser(Base):
    id: uuid.UUID
    uid: str
    username: str
    username_lower: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    profile_picture_id: Optional[uuid.UUID]
    profile_picture_url: Optional[str]
    profile_picture_blob_name: Optional[str]
    is_featured: bool
    is_admin: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime
    post_count: int
    follower_count: int
    following_count: int


class InternalPost(Base):
    id: uuid.UUID
    user_id: uuid.UUID
    place_id: uuid.UUID
    category: str
    custom_latitude: Optional[float]
    custom_longitude: Optional[float]
    content: str
    image_id: Optional[uuid.UUID]
    image_url: Optional[str]
    image_blob_name: Optional[str]
    deleted: bool
    created_at: datetime


class InternalComment(Base):
    id: uuid.UUID
    user_id: uuid.UUID
    post_id: uuid.UUID
    content: str
    deleted: bool
    created_at: datetime
