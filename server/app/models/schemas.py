from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator, root_validator

from app.models.models import Category


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split('_')
    return parts[0] + "".join(part.title() for part in parts[1:])


class Location(BaseModel):
    latitude: float
    longitude: float

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class Region(Location):
    radius: float


class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    post_count: int
    follower_count: int
    following_count: int

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class UserPrefs(BaseModel):
    post_notifications: bool
    follow_notifications: bool
    post_liked_notifications: bool

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class PublicUser(UserBase):
    pass


class PrivateUser(UserBase):
    email: str
    private_account: bool
    preferences: Optional[UserPrefs]
    created_at: datetime

    @validator("created_at", pre=True)
    def get_created_at(cls, created_at: datetime):  # noqa
        return created_at.replace(microsecond=0)


class Place(BaseModel):
    urlsafe_id: str = Field(alias="placeId")
    name: str
    category: str
    location: Location
    region: Region

    @validator("category", pre=True)
    def get_category(cls, category: Category):
        return category.name

    @root_validator(pre=True)
    def get_location(cls, values):
        assert "latitude" in values, "latitude should be in values"
        assert "longitude" in values, "longitude should be in values"
        return dict(values, location=Location(latitude=values["latitude"], longitude=values["longitude"]))

    @root_validator(pre=True)
    def get_region(cls, values):
        assert "region_center_lat" in values, "region_center_lat should be in values"
        assert "region_center_long" in values, "region_center_long should be in values"
        assert "radius_meters" in values, "radius_meters should be in values"
        return dict(values, region=Region(latitude=values["region_center_lat"],
                                          longitude=values["region_center_long"],
                                          radius=values["radius_meters"]))

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class Post(BaseModel):
    urlsafe_id: str = Field(alias="postId")
    user: PublicUser
    place: Place
    content: str
    image_url: str
    created_at: datetime
    tags: List[str]
    like_count: int
    comment_count: int
    custom_location: Optional[Location]

    @validator("created_at", pre=True)
    def get_created_at(cls, created_at: datetime):  # noqa
        return created_at.replace(microsecond=0)

    @validator("tags", pre=True)
    def get_tags(cls, tags):  # noqa
        # tags is a SQLAlchemy association list, and we need to convert
        # to a Python list so Pydantic can recognize it
        return list(tags)

    @root_validator(pre=True)
    def get_location(cls, values):
        if values.get("custom_location") is None:
            return values
        assert "custom_latitude" in values, "custom_latitude should be in values"
        assert "custom_longitude" in values, "custom_longitude should be in values"
        return dict(values,
                    custom_location=Location(latitude=values["custom_latitude"], longitude=values["custom_longitude"]))

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case


class Comment(BaseModel):
    urlsafe_id: str = Field(alias="commentId")
    user: PublicUser
    post_id: int
    content: str
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        alias_generator = to_camel_case
