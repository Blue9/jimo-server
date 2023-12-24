from enum import Enum
from pydantic import field_validator
from app.core.types import Base, PlaceId


class OnboardingCity(Enum):
    NYC = "New York"
    LA = "Los Angeles"
    CHICAGO = "Chicago"
    LONDON = "London"


class PlaceTile(Base):
    place_id: str
    name: str
    image_url: str
    category: str
    description: str


class PlaceTilePage(Base):
    places: list[PlaceTile]
    cursor: PlaceId | None = None


class MinimalSavePlaceRequest(Base):
    place_id: PlaceId


class MinimalCreatePostRequest(Base):
    place_id: PlaceId
    category: str
    stars: int | None = None

    @field_validator("stars")
    @classmethod
    def validate_stars(cls, stars):
        if stars is not None and (stars < 0 or stars > 3):
            raise ValueError("Can only award between 0 and 3 stars")
        return stars


class CreateMultiRequest(Base):
    city: str | None = None
    posts: list[MinimalCreatePostRequest]
    saves: list[MinimalSavePlaceRequest]

    @field_validator("posts")
    @classmethod
    def validate_posts(cls, posts):
        if len(posts) > 20:
            raise ValueError("Max length is 20")
        return posts

    @field_validator("saves")
    @classmethod
    def validate_places(cls, places):
        if len(places) > 20:
            raise ValueError("Max length is 20")
        return places
