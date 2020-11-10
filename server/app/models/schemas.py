from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


def to_camel_case(snake_case: str) -> str:
    if not snake_case:
        return snake_case
    parts = snake_case.split('_')
    return parts[0] + "".join(part.title() for part in parts[1:])


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


class PublicUser(UserBase):
    pass


class PrivateUser(UserBase):
    email: str
    created_at: datetime
    login_methods: List[str]

    @validator("login_methods", pre=True)
    def get_login_methods(cls, login_methods):  # noqa
        # tags is a SQLAlchemy association list, and we need to convert
        # to a Python list so Pydantic can recognize it
        return list(login_methods)


class Post(BaseModel):
    urlsafe_id: str = Field(alias="postId")
    user: PublicUser
    place_id: int  # TODO(gmekkat): make place object
    content: str
    image_url: str
    created_at: datetime
    tags: List[str]
    like_count: int
    comment_count: int

    @validator("tags", pre=True)
    def get_tags(cls, tags):  # noqa
        # tags is a SQLAlchemy association list, and we need to convert
        # to a Python list so Pydantic can recognize it
        return list(tags)

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
