from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator, root_validator


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split('_')
    return parts[0] + "".join(part.title() for part in parts[1:])


class Base(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class Location(Base):
    latitude: float
    longitude: float

    @validator("latitude")
    def validate_latitude(cls, latitude):
        if latitude < -90 or latitude > 90:
            raise ValueError("Invalid latitude")
        return latitude

    @validator("longitude")
    def validate_longitude(cls, longitude):
        if longitude < -180 or longitude > 180:
            raise ValueError("Invalid longitude")
        return longitude


class Region(Location):
    radius: float

    @validator("radius")
    def validate_radius(cls, radius):
        if radius < 0 or radius > 10e6:
            # Russia is about 9,000 km wide, so 10,000 km is a fair upper bound
            raise ValueError("Invalid radius")
        return radius


class PublicUser(Base):
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    post_count: int
    follower_count: int
    following_count: int


class UserPrefs(Base):
    post_notifications: bool
    follow_notifications: bool
    post_liked_notifications: bool


class PrivateUser(PublicUser):
    uid: str
    preferences: Optional[UserPrefs]


class Place(Base):
    urlsafe_id: str = Field(alias="placeId")
    name: str
    location: Location

    @root_validator(pre=True)
    def get_location(cls, values):
        if values.get("latitude") is not None and values.get("longitude") is not None:
            return dict(values, location=Location(latitude=values["latitude"], longitude=values["longitude"]))
        return values


class ORMPost(Base):
    urlsafe_id: str = Field(alias="postId")
    user: PublicUser
    place: Place
    category: str
    content: str
    image_url: Optional[str]
    created_at: datetime
    like_count: int
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


class Post(ORMPost):
    liked: bool


# Not used for now
class Comment(Base):
    urlsafe_id: str = Field(alias="commentId")
    user: PublicUser
    post: str  # This is the post ID
    content: str
    created_at: datetime

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Swift can't automatically decode w/ milliseconds
        return created_at.replace(microsecond=0)

    @root_validator(pre=True)
    def get_post_id(cls, values):  # noqa
        assert "post" in values, "post should be in values"
        return dict(values, post=values["post"].urlsafe_id)
