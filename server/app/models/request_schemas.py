from typing import Optional

from pydantic import validator
from pydantic.main import BaseModel

from app.models import validators
from app.models.schemas import to_camel_case, Location, Region


class CreateUserRequest(BaseModel):
    username: str
    first_name: str
    last_name: str

    @validator("username")
    def validate_username(cls, username: str):
        username = username.strip()
        if not validators.is_valid_username(username):
            raise ValueError("Username must be 3-20 characters and alphanumeric")
        return username

    @validator("first_name")
    def validate_first_name(cls, first_name: str):
        first_name = first_name.strip()
        if not validators.is_valid_name(first_name):
            raise ValueError("First name must be 1-100 characters")
        return first_name

    @validator("last_name")
    def validate_last_name(cls, last_name: str):
        last_name = last_name.strip()
        if not validators.is_valid_name(last_name):
            raise ValueError("First name must be 1-100 characters")
        return last_name

    class Config:
        alias_generator = to_camel_case


class UpdateUserRequest(BaseModel):
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    private_account: Optional[bool]

    post_notifications: Optional[bool]
    follow_notifications: Optional[bool]
    post_liked_notifications: Optional[bool]

    @validator("username")
    def validate_username(cls, username):
        if username is None:
            return
        return CreateUserRequest.validate_username(username)

    @validator("first_name")
    def validate_first_name(cls, first_name):
        if first_name is None:
            return
        return CreateUserRequest.validate_first_name(first_name)

    @validator("last_name")
    def validate_last_name(cls, last_name):
        if last_name is None:
            return
        return CreateUserRequest.validate_last_name(last_name)

    class Config:
        alias_generator = to_camel_case


class MaybeCreatePlaceRequest(BaseModel):
    name: str
    location: Location
    region: Optional[Region]

    @validator("name")
    def validate_name(cls, name):
        name = name.strip()
        if len(name) == 0 or len(name) > 1000:
            raise ValueError("Invalid name")
        return name

    class Config:
        alias_generator = to_camel_case


class CreatePostRequest(BaseModel):
    place: MaybeCreatePlaceRequest
    category: str
    content: str
    image_url: Optional[str]
    # tags: List[str]
    custom_location: Optional[Location]

    class Config:
        alias_generator = to_camel_case
