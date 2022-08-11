from typing import Optional

from pydantic import validator
from shared.api.base import Base, Category
from shared.api.map import MapPinV3
from shared.api.place import Region
from shared.api.type_aliases import UserId


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
