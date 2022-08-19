from datetime import datetime
from typing import Optional

from pydantic import Field, validator

from app.features.places.entities import Place
from app.features.users.entities import PublicUser
from app.core.types import Base, PostId, ImageId, InternalBase, UserId, PostSaveId


class PostWithoutLikeSaveStatus(Base):
    id: PostId = Field(alias="postId")
    user: PublicUser
    place: Place
    category: str
    content: str
    image_url: Optional[str]
    image_id: Optional[ImageId]
    created_at: datetime
    like_count: int
    comment_count: int

    @validator("content")
    def validate_content(cls, content):
        return content.strip()

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class Post(PostWithoutLikeSaveStatus):
    liked: bool
    saved: bool


class InternalPost(InternalBase):
    id: PostId
    user_id: UserId
    place: Place
    category: str
    custom_latitude: Optional[float]
    custom_longitude: Optional[float]
    content: str
    image_id: Optional[ImageId]
    image_url: Optional[str]
    image_blob_name: Optional[str]
    deleted: bool
    created_at: datetime
    like_count: int
    comment_count: int


class InternalPostSave(InternalBase):
    id: PostSaveId
    user_id: UserId
    post_id: PostId
