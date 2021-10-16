import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field, validator, root_validator

from shared.schemas.base import Base
from shared.schemas.place import Place, Location, MaybeCreatePlaceRequest
from shared.schemas.user import PublicUser


# ORM types
class ORMPostWithoutUser(Base):
    id: uuid.UUID = Field(alias="postId")
    place: Place
    category: str
    content: str
    image_url: Optional[str]
    created_at: datetime
    like_count: int
    comment_count: int
    custom_location: Optional[Location]

    @validator("content")
    def validate_content(cls, content):
        return content.strip()

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)

    @root_validator(pre=True)
    def get_location(cls, values):
        if values.get("custom_latitude") is not None and values.get("custom_longitude") is not None:
            return dict(values, custom_location=Location(latitude=values["custom_latitude"],
                                                         longitude=values["custom_longitude"]))
        return values


class ORMPost(ORMPostWithoutUser):
    user: PublicUser


class Post(ORMPost):
    liked: bool


# Request types
class CreatePostRequest(Base):
    place: MaybeCreatePlaceRequest
    category: str
    content: str
    image_id: Optional[uuid.UUID]
    custom_location: Optional[Location]

    @validator("content")
    def validate_content(cls, content):
        content = content.strip()
        if len(content) > 2000:
            raise ValueError("Note too long (max length 2000 chars)")
        return content


class ReportPostRequest(Base):
    details: Optional[str]

    @validator("details")
    def validate_details(cls, details):
        details = details.strip()
        if len(details) > 2000:
            raise ValueError("Max length is 2000 characters")
        return details


# Response types
class Feed(Base):
    posts: list[Post]
    cursor: Optional[uuid.UUID]


class LikePostResponse(Base):
    likes: int


class DeletePostResponse(Base):
    deleted: bool
