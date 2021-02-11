from typing import Optional

from pydantic import validator, root_validator

from app.models import validators
from app.models.schemas import Base, Location, Region


class CreateUserRequest(Base):
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
            raise ValueError("Last name must be 1-100 characters")
        return last_name


class UpdateUserRequest(Base):
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    private_account: Optional[bool]

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


class InviteUserRequest(Base):
    phone_number: str

    @validator("phone_number")
    def validate_phone_number(cls, phone_number):
        # TODO make sure it's in e164 format
        return phone_number


class MaybeCreatePlaceRequest(Base):
    name: str
    location: Location
    region: Optional[Region]

    @validator("name")
    def validate_name(cls, name):
        name = name.strip()
        if len(name) == 0 or len(name) > 1000:
            raise ValueError("Invalid name")
        return name


class CreatePostRequest(Base):
    place: MaybeCreatePlaceRequest
    category: str
    content: str
    image_url: Optional[str]
    custom_location: Optional[Location]


class RectangularRegion(Base):
    center_lat: float
    center_long: float
    span_lat: float
    span_long: float

    @root_validator(pre=True)
    def get_region(cls, values):
        assert -90 <= values.get("center_lat") <= 90
        assert -180 <= values.get("center_long") <= 180
        assert 0 <= values.get("span_lat") <= 180
        assert 0 <= values.get("span_long") <= 360
        return values


class NotificationTokenRequest(Base):
    token: str


class PhoneNumberList(Base):
    phone_numbers: list[str]

    @validator("phone_numbers")
    def validate_phone_numbers(cls, phone_numbers):
        # TODO make sure each number is in e164 format
        return phone_numbers
