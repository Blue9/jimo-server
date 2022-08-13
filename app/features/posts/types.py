from typing import Optional

from pydantic import root_validator, validator

from app.core.types import Base, ImageId, CursorId, PlaceId
from app.features.places.entities import Location, Region, AdditionalPlaceData
from app.features.posts.entities import Post


class MaybeCreatePlaceRequest(Base):
    name: str
    location: Location
    region: Optional[Region]
    additional_data: Optional[AdditionalPlaceData]

    @validator("name")
    def validate_name(cls, name):
        name = name.strip()
        if len(name) == 0 or len(name) > 1000:
            raise ValueError("Invalid name")
        return name


class CreatePostRequest(Base):
    place_id: Optional[PlaceId]
    place: Optional[MaybeCreatePlaceRequest]
    category: str
    content: str
    image_id: Optional[ImageId]

    @root_validator
    def validate_place(cls, values):
        assert values.get("place_id") is not None or values.get("place") is not None, "place must be included"
        return values

    @validator("content")
    def validate_content(cls, content):
        content = content.strip()
        if len(content) > 2000:
            raise ValueError("Caption too long (max length 2000 chars)")
        return content


class ReportPostRequest(Base):
    details: Optional[str]

    @validator("details")
    def validate_details(cls, details):
        details = details.strip()
        if len(details) > 2000:
            raise ValueError("Max length is 2000 characters")
        return details


class PostFeedResponse(Base):
    posts: list[Post]
    cursor: Optional[CursorId]


class LikePostResponse(Base):
    likes: int


class DeletePostResponse(Base):
    deleted: bool
