from datetime import datetime

from pydantic import Field, validator
from app.features.images.entities import MediaEntity

from app.features.places.entities import Place
from app.features.users.entities import PublicUser
from app.core.types import Base, PostId, ImageId, InternalBase, UserId, PostSaveId


class PostWithoutLikeSaveStatus(Base):
    id: PostId = Field(alias="postId")
    user: PublicUser
    place: Place
    category: str
    content: str
    stars: int | None = None
    image_url: str | None = None
    image_id: ImageId | None = None
    media: list[MediaEntity] | None
    created_at: datetime
    like_count: int
    comment_count: int

    @validator("image_id", pre=True, always=True)
    def set_image_id(cls, image_id, values):
        if values.get("media"):
            return values["media"][0].id
        return image_id

    @validator("image_url", pre=True, always=True)
    def set_image_url(cls, image_url, values):
        if values.get("media"):
            return values["media"][0].url
        return image_url

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
    content: str
    stars: int | None
    image_id: ImageId | None
    image_url: str | None
    image_blob_name: str | None
    media: list[MediaEntity] | None
    deleted: bool
    created_at: datetime
    like_count: int
    comment_count: int


class InternalPostSave(InternalBase):
    id: PostSaveId
    user_id: UserId
    post_id: PostId
