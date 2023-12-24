from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from app.features.images.entities import MediaEntity

from app.features.places.entities import Place
from app.features.users.entities import PublicUser
from app.core.types import Base, PostId, ImageId, InternalBase, UserId, PostSaveId


class PostWithoutLikeSaveStatus(Base):
    id: PostId = Field(serialization_alias="postId")
    user: PublicUser
    place: Place
    category: str
    content: str
    stars: int | None = None
    image_url: str | None = None
    image_id: ImageId | None = None
    media: list[MediaEntity]
    created_at: datetime
    like_count: int
    comment_count: int

    @model_validator(mode="after")
    @classmethod
    def set_image_id_and_url(cls, values):
        if len(values.media) > 0:
            values.image_id = UUID(values.media[0].id)
            values.image_url = values.media[0].url
        return values

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, created_at: datetime) -> datetime:
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
    media: list[MediaEntity]
    deleted: bool
    created_at: datetime
    like_count: int
    comment_count: int


class InternalPostSave(InternalBase):
    id: PostSaveId
    user_id: UserId
    post_id: PostId
