from pydantic import field_validator, model_validator

from app.core.types import Base, ImageId, CursorId, PlaceId
from app.features.places.entities import Location, Region, AdditionalPlaceData, SavedPlace
from app.features.posts.entities import Post


class MaybeCreatePlaceWithMetadataRequest(Base):
    name: str
    location: Location
    region: Region | None = None
    additional_data: AdditionalPlaceData | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, name):
        name = name.strip()
        if len(name) == 0 or len(name) > 1000:
            raise ValueError("Invalid name")
        return name


class CreatePostRequest(Base):
    place_id: PlaceId | None = None
    place: MaybeCreatePlaceWithMetadataRequest | None = None
    category: str
    content: str
    image_id: ImageId | None = None  # deprecated, use media field
    media: list[ImageId] = []
    stars: int | None = None

    @model_validator(mode="after")
    @classmethod
    def validate_all(cls, values):
        # validate place
        assert values.place_id is not None or values.place is not None, "place must be included"
        # handle backwards compat for image_id
        if values.image_id and len(values.media) == 0:
            values.media = [values.image_id]
        return values

    @field_validator("stars")
    @classmethod
    def validate_stars(cls, stars):
        if stars is not None and (stars < 0 or stars > 3):
            raise ValueError("Can only award between 0 and 3 stars")
        return stars

    @field_validator("content")
    @classmethod
    def validate_content(cls, content):
        content = content.strip()
        if len(content) > 2000:
            raise ValueError("Caption too long (max length 2000 chars)")
        return content


class ReportPostRequest(Base):
    details: str | None = None

    @field_validator("details")
    @classmethod
    def validate_details(cls, details):
        details = details.strip()
        if len(details) > 2000:
            raise ValueError("Max length is 2000 characters")
        return details


class PaginatedPosts(Base):
    posts: list[Post]
    cursor: CursorId | None = None


class LikePostResponse(Base):
    likes: int


class SavePostResponse(Base):
    success: bool  # backwards-compatibility
    save: SavedPlace


class DeletePostResponse(Base):
    deleted: bool
