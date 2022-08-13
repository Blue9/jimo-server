from typing import Optional

from pydantic import validator

from app.core.types import Base, Category, UserId
from app.features.map.entities import MapPinV3
from app.features.places.entities import Region


class GetMapRequest(Base):
    region: Region
    categories: Optional[list[Category]]


class CustomMapRequest(GetMapRequest):
    users: list[UserId]

    @validator("users")
    def validate_users(cls, users):
        if len(users) > 100:
            raise ValueError("User list too long, max length is 100")
        return users


class PlaceLoadRequest(Base):
    categories: Optional[list[Category]]


class CustomPlaceLoadRequest(PlaceLoadRequest):
    users: list[UserId]

    @validator("users")
    def validate_users(cls, users):
        if len(users) > 100:
            raise ValueError("User list too long, max length is 100")
        return users


class MapResponseV3(Base):
    pins: list[MapPinV3]
