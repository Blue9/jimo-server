from typing import Optional

from pydantic import validator

from app.core.types import Base, Category, UserId
from app.features.map.entities import MapPin, MapType
from app.features.places.entities import Region, RectangularRegion


class GetMapRequest(Base):
    region: RectangularRegion
    categories: list[Category] | None
    map_type: MapType
    user_ids: list[UserId] | None

    @validator("user_ids")
    def validate_user_ids(cls, user_ids):
        if len(user_ids) > 100:
            raise ValueError("User list too long, max length is 100")
        return user_ids


class DeprecatedGetMapRequest(Base):
    region: Region
    categories: Optional[list[Category]]


class DeprecatedCustomMapRequest(DeprecatedGetMapRequest):
    users: list[UserId]

    @validator("users")
    def validate_users(cls, users):
        if len(users) > 100:
            raise ValueError("User list too long, max length is 100")
        return users


class DeprecatedPlaceLoadRequest(Base):
    categories: Optional[list[Category]]


class DeprecatedCustomPlaceLoadRequest(DeprecatedPlaceLoadRequest):
    users: list[UserId]

    @validator("users")
    def validate_users(cls, users):
        if len(users) > 100:
            raise ValueError("User list too long, max length is 100")
        return users


class GetMapResponse(Base):
    pins: list[MapPin]
